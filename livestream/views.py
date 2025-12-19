from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import LiveStream, LiveStreamComment, LiveStreamView
from .serializers import (
    LiveStreamSerializer, LiveStreamOwnerSerializer, LiveStreamCreateSerializer, 
    LiveStreamCommentSerializer, LiveStreamViewSerializer,
    LiveStreamListSerializer
)
from .ivs_service import IVSService
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class LiveStreamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing live streams
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Return user's own streams or public live streams
        return LiveStream.objects.filter(
            Q(user=user) | Q(status='live')
        ).select_related('user').distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LiveStreamCreateSerializer
        elif self.action == 'list':
            return LiveStreamListSerializer
        return LiveStreamSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to return stream_key only to owner"""
        instance = self.get_object()
        # Use owner serializer if user is the owner
        if request.user == instance.user:
            serializer = LiveStreamOwnerSerializer(instance, context=self.get_serializer_context())
        else:
            serializer = LiveStreamSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new live stream and AWS IVS channel
        Reuses existing channel if user has one that's not currently live
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Check for existing channel that can be reused
            # Look for a recent stream by this user that has channel info
            existing_stream = LiveStream.objects.filter(
                user=request.user,
                channel_arn__isnull=False,
                stream_key__isnull=False
            ).exclude(
                channel_arn='',
                stream_key=''
            ).order_by('-created_at').first()
            
            if existing_stream and existing_stream.channel_arn and existing_stream.stream_key:
                # Reuse existing channel
                logger.info(f"Reusing existing IVS channel for user {request.user.id}")
                
                # Create new livestream with existing channel info
                livestream = LiveStream.objects.create(
                    user=request.user,
                    title=serializer.validated_data.get('title', ''),
                    description=serializer.validated_data.get('description', ''),
                    channel_arn=existing_stream.channel_arn,
                    playback_url=existing_stream.playback_url,
                    ingest_endpoint=existing_stream.ingest_endpoint,
                    stream_key=existing_stream.stream_key,
                    status='preparing'
                )
                
                # Return the created stream with full details including stream_key for the owner
                response_serializer = LiveStreamOwnerSerializer(livestream)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            # Check if IVS is configured
            if not all([
                hasattr(settings, 'AWS_ACCESS_KEY_ID'),
                hasattr(settings, 'AWS_SECRET_ACCESS_KEY'),
                hasattr(settings, 'AWS_REGION')
            ]):
                # Fallback: use existing channel ARN if configured
                if hasattr(settings, 'AWS_IVS_CHANNEL_ARN'):
                    livestream = LiveStream.objects.create(
                        user=request.user,
                        title=serializer.validated_data.get('title', ''),
                        description=serializer.validated_data.get('description', ''),
                        channel_arn=settings.AWS_IVS_CHANNEL_ARN,
                        playback_url=getattr(settings, 'AWS_IVS_PLAYBACK_URL', ''),
                        ingest_endpoint=getattr(settings, 'AWS_IVS_INGEST_ENDPOINT', ''),
                        stream_key=getattr(settings, 'AWS_IVS_STREAM_KEY', ''),
                        status='preparing'
                    )
                else:
                    return Response(
                        {'error': 'AWS IVS not configured. Please configure AWS credentials or channel ARN.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Create IVS channel
                ivs_service = IVSService()
                # Use only alphanumeric, hyphens, and underscores for channel name
                timestamp = str(int(timezone.now().timestamp()))
                channel_name = f"livestream-{str(request.user.id).replace('-', '')[:12]}-{timestamp}"
                
                try:
                    channel_info = ivs_service.create_channel(channel_name)
                except Exception as e:
                    logger.error(f"Failed to create IVS channel: {str(e)}")
                    # Fallback to manual configuration if available
                    if hasattr(settings, 'AWS_IVS_CHANNEL_ARN'):
                        channel_info = {
                            'channel_arn': settings.AWS_IVS_CHANNEL_ARN,
                            'playback_url': getattr(settings, 'AWS_IVS_PLAYBACK_URL', ''),
                            'ingest_endpoint': getattr(settings, 'AWS_IVS_INGEST_ENDPOINT', ''),
                            'stream_key': getattr(settings, 'AWS_IVS_STREAM_KEY', ''),
                        }
                    else:
                        return Response(
                            {'error': f'Failed to create IVS channel: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                
                # Create LiveStream object
                livestream = LiveStream.objects.create(
                    user=request.user,
                    title=serializer.validated_data.get('title', ''),
                    description=serializer.validated_data.get('description', ''),
                    channel_arn=channel_info['channel_arn'],
                    playback_url=channel_info['playback_url'],
                    ingest_endpoint=channel_info['ingest_endpoint'],
                    stream_key=channel_info['stream_key'],
                    status='preparing'
                )
            
            # Return the created stream with full details including stream_key for the owner
            response_serializer = LiveStreamOwnerSerializer(livestream)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating live stream: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start a live stream
        """
        livestream = self.get_object()
        
        # Only the owner can start their stream
        if livestream.user != request.user:
            return Response(
                {'error': 'You can only start your own live streams'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        livestream.status = 'live'
        livestream.started_at = timezone.now()
        livestream.viewer_count = 0  # Reset viewer count when starting
        livestream.save()
        
        serializer = self.get_serializer(livestream)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """
        End a live stream
        """
        livestream = self.get_object()
        
        # Only the owner can end their stream
        if livestream.user != request.user:
            return Response(
                {'error': 'You can only end your own live streams'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        livestream.status = 'ended'
        livestream.ended_at = timezone.now()
        livestream.viewer_count = 0  # Reset viewer count when ending
        livestream.save()
        
        # Optionally stop the stream on AWS IVS
        try:
            if hasattr(settings, 'AWS_ACCESS_KEY_ID'):
                ivs_service = IVSService()
                ivs_service.stop_stream(livestream.channel_arn)
        except Exception as e:
            logger.warning(f"Failed to stop IVS stream: {str(e)}")
        
        serializer = self.get_serializer(livestream)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """
        Check the current status of a live stream from AWS IVS
        """
        livestream = self.get_object()
        
        try:
            if hasattr(settings, 'AWS_ACCESS_KEY_ID'):
                ivs_service = IVSService()
                stream_state = ivs_service.get_stream_state(livestream.channel_arn)
                
                # Update livestream status based on AWS state
                aws_state = stream_state.get('state', 'OFFLINE')
                if aws_state == 'LIVE' and livestream.status != 'live':
                    livestream.status = 'live'
                    if not livestream.started_at:
                        livestream.started_at = timezone.now()
                    livestream.save()
                
                return Response({
                    'livestream_id': str(livestream.id),
                    'status': livestream.status,
                    'aws_state': aws_state,
                    'stream_info': stream_state
                })
            else:
                return Response({
                    'livestream_id': str(livestream.id),
                    'status': livestream.status,
                    'message': 'AWS IVS not configured for status checks'
                })
        except Exception as e:
            logger.error(f"Error checking stream status: {str(e)}")
            return Response({
                'livestream_id': str(livestream.id),
                'status': livestream.status,
                'error': str(e)
            })
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all currently live streams (public endpoint for feed)
        Returns streams with status 'live' or 'preparing'
        """
        active_streams = LiveStream.objects.filter(
            status__in=['live', 'preparing']
        ).select_related('user').order_by('-created_at')
        
        serializer = LiveStreamListSerializer(active_streams, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all currently active (live) streams
        """
        active_streams = LiveStream.objects.filter(
            status='live'
        ).select_related('user').order_by('-started_at')
        
        serializer = LiveStreamListSerializer(active_streams, many=True)
        return Response(serializer.data)


class LiveStreamCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing live stream comments
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LiveStreamCommentSerializer
    
    def get_queryset(self):
        livestream_id = self.request.query_params.get('livestream')
        queryset = LiveStreamComment.objects.select_related('user', 'livestream')
        
        if livestream_id:
            queryset = queryset.filter(livestream_id=livestream_id)
        
        return queryset.order_by('created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LiveStreamViewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tracking live stream views
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LiveStreamViewSerializer
    
    def get_queryset(self):
        return LiveStreamView.objects.filter(
            user=self.request.user
        ).select_related('user', 'livestream')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        Mark when a user leaves a live stream
        """
        view = self.get_object()
        view.left_at = timezone.now()
        view.save()
        
        # Update viewer count
        livestream = view.livestream
        active_viewers = LiveStreamView.objects.filter(
            livestream=livestream,
            left_at__isnull=True
        ).count()
        
        livestream.viewer_count = active_viewers
        livestream.save()
        
        serializer = self.get_serializer(view)
        return Response(serializer.data)
