import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import LiveStream, LiveStreamComment
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)
User = get_user_model()


class LiveStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live stream real-time features
    - Real-time comments
    - Viewer count updates
    - Stream status updates
    """
    
    async def connect(self):
        self.livestream_id = self.scope['url_route']['kwargs']['livestream_id']
        self.room_group_name = f'livestream_{self.livestream_id}'
        self.is_streamer = False  # Will be set when user identifies themselves
        self.is_counted = False   # Track if this connection has been counted
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current viewer count to the new user (don't increment yet)
        viewer_count = await self.get_viewer_count()
        await self.send(text_data=json.dumps({
            'type': 'viewer_count',
            'count': viewer_count
        }))
    
    async def disconnect(self, close_code):
        # Only decrement if this connection was counted
        if self.is_counted:
            viewer_count = await self.update_viewer_count(-1)
            
            # Broadcast updated viewer count to remaining users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_viewer_count',
                    'count': viewer_count
                }
            )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'comment':
                await self.handle_comment(data)
            elif message_type == 'like':
                await self.handle_like(data)
            elif message_type == 'identify':
                await self.handle_identify(data)
            elif message_type == 'viewer_joined':
                await self.handle_viewer_joined(data)
            
        except Exception as e:
            logger.error(f"Error in LiveStreamConsumer.receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process message'
            }))
    
    async def handle_identify(self, data):
        """
        Handle user identification - streamer or viewer
        """
        is_streamer = data.get('is_streamer', False)
        self.is_streamer = is_streamer
        
        # Only count viewers, not streamers
        if not is_streamer and not self.is_counted:
            self.is_counted = True
            viewer_count = await self.update_viewer_count(1)
            
            # Broadcast updated viewer count to all users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_viewer_count',
                    'count': viewer_count
                }
            )
        elif is_streamer:
            # Streamer doesn't count but should get current viewer count
            viewer_count = await self.get_viewer_count()
            await self.send(text_data=json.dumps({
                'type': 'viewer_count',
                'count': viewer_count
            }))
    
    async def handle_comment(self, data):
        """
        Handle new comment
        """
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            return
        
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Authentication required'
            }))
            return
        
        # Save comment to database
        comment = await self.save_comment(user, comment_text)
        
        if comment:
            # Broadcast comment to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_comment',
                    'comment': {
                        'id': str(comment['id']),
                        'user': comment['user'],
                        'comment': comment['comment'],
                        'created_at': comment['created_at']
                    }
                }
            )
    
    async def handle_like(self, data):
        """
        Handle like action
        """
        # Broadcast like to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_like',
                'user_id': str(self.scope['user'].id) if self.scope.get('user') else None
            }
        )
    
    async def handle_viewer_joined(self, data):
        """
        Handle viewer joined event
        """
        viewer_count = await self.get_viewer_count()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_viewer_count',
                'count': viewer_count
            }
        )
    
    async def broadcast_comment(self, event):
        """
        Broadcast comment to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'comment',
            'comment': event['comment']
        }))
    
    async def broadcast_like(self, event):
        """
        Broadcast like to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'like',
            'user_id': event.get('user_id')
        }))
    
    async def broadcast_viewer_count(self, event):
        """
        Broadcast viewer count to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'viewer_count',
            'count': event['count']
        }))
    
    async def stream_status(self, event):
        """
        Broadcast stream status updates
        """
        await self.send(text_data=json.dumps({
            'type': 'stream_status',
            'status': event['status']
        }))
    
    @database_sync_to_async
    def save_comment(self, user, comment_text):
        """
        Save comment to database
        """
        try:
            livestream = LiveStream.objects.get(id=self.livestream_id)
            comment = LiveStreamComment.objects.create(
                livestream=livestream,
                user=user,
                comment=comment_text
            )
            headers = dict(self.scope.get('headers', []))
            host = headers.get(b'host', b'').decode('utf-8')
            scheme = 'https' if self.scope.get('scheme') == 'https' else 'http'
            
            return {
                'id': comment.id,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'profile_name': getattr(user, 'profile_name', user.email.split('@')[0]),
                    'profile_image': urljoin(f"{scheme}://{host}", user.profile_image.url) if hasattr(user, 'profile_image') and user.profile_image else None
                },
                'comment': comment.comment,
                'created_at': comment.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Error saving comment: {str(e)}")
            return None
    
    @database_sync_to_async
    def update_viewer_count(self, delta):
        """
        Update viewer count for the livestream
        """
        try:
            livestream = LiveStream.objects.get(id=self.livestream_id)
            livestream.viewer_count = max(0, livestream.viewer_count + delta)
            
            # Update peak viewers
            if livestream.viewer_count > livestream.peak_viewers:
                livestream.peak_viewers = livestream.viewer_count
            
            livestream.save(update_fields=['viewer_count', 'peak_viewers'])
            return livestream.viewer_count
        except Exception as e:
            logger.error(f"Error updating viewer count: {str(e)}")
            return 0
    
    @database_sync_to_async
    def get_viewer_count(self):
        """
        Get current viewer count
        """
        try:
            livestream = LiveStream.objects.get(id=self.livestream_id)
            return livestream.viewer_count
        except Exception as e:
            logger.error(f"Error getting viewer count: {str(e)}")
            return 0
