import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class IVSService:
    """
    Service class for interacting with AWS IVS
    """
    
    def __init__(self):
        self.client = boto3.client(
            'ivs',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    
    def create_channel(self, name, latency_mode='LOW'):
        """
        Create a new IVS channel
        
        Args:
            name: Channel name
            latency_mode: 'LOW' or 'NORMAL'
        
        Returns:
            dict: Channel information including ARN, playback URL, and ingest endpoint
        """
        try:
            response = self.client.create_channel(
                name=name,
                latencyMode=latency_mode,
                type='STANDARD',  # or 'BASIC'
                authorized=False  # Set to True for private streams
            )
            
            channel = response['channel']
            stream_key = response['streamKey']
            
            return {
                'channel_arn': channel['arn'],
                'playback_url': channel['playbackUrl'],
                'ingest_endpoint': channel['ingestEndpoint'],
                'stream_key': stream_key['value']
            }
        except Exception as e:
            logger.error(f"Error creating IVS channel: {str(e)}")
            raise
    
    def create_stream_key(self, channel_arn):
        """
        Create a new stream key for an existing channel
        
        Args:
            channel_arn: ARN of the channel
        
        Returns:
            str: Stream key value
        """
        try:
            response = self.client.create_stream_key(
                channelArn=channel_arn
            )
            return response['streamKey']['value']
        except Exception as e:
            logger.error(f"Error creating stream key: {str(e)}")
            raise
    
    def get_channel(self, channel_arn):
        """
        Get channel information
        
        Args:
            channel_arn: ARN of the channel
        
        Returns:
            dict: Channel information
        """
        try:
            response = self.client.get_channel(arn=channel_arn)
            return response['channel']
        except Exception as e:
            logger.error(f"Error getting channel: {str(e)}")
            raise
    
    def get_stream_state(self, channel_arn):
        """
        Get the current state of a stream
        
        Args:
            channel_arn: ARN of the channel
        
        Returns:
            dict: Stream state information (LIVE, OFFLINE, etc.)
        """
        try:
            response = self.client.get_stream(channelArn=channel_arn)
            return response.get('stream', {})
        except self.client.exceptions.ChannelNotBroadcasting:
            return {'state': 'OFFLINE'}
        except Exception as e:
            logger.error(f"Error getting stream state: {str(e)}")
            return {'state': 'UNKNOWN'}
    
    def delete_channel(self, channel_arn):
        """
        Delete an IVS channel
        
        Args:
            channel_arn: ARN of the channel
        """
        try:
            self.client.delete_channel(arn=channel_arn)
            return True
        except Exception as e:
            logger.error(f"Error deleting channel: {str(e)}")
            raise
    
    def stop_stream(self, channel_arn):
        """
        Stop a live stream
        
        Args:
            channel_arn: ARN of the channel
        """
        try:
            self.client.stop_stream(channelArn=channel_arn)
            return True
        except Exception as e:
            logger.error(f"Error stopping stream: {str(e)}")
            raise
