from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Max, Prefetch
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import os
import magic
import uuid

from .models import Conversation, Message, GlobalChatMessage, MessageReadReceipt, Call
from .serializers import (
    ConversationSerializer, ConversationListSerializer,
    MessageSerializer, GlobalChatMessageSerializer,
    MessageReadReceiptSerializer, CallSerializer
)

User = get_user_model()

# ============== Custom Pagination Classes ==============

class MessagePagination(PageNumberPagination):
    """Pagination for private chat messages"""
    page_size = 30  # Load 30 messages at a time
    page_size_query_param = 'page_size'
    max_page_size = 100


class GlobalChatPagination(PageNumberPagination):
    """Pagination for global chat messages"""
    page_size = 10  # Load only last 10 messages initially
    page_size_query_param = 'page_size'
    max_page_size = 50

# Allowed file types for upload (MIME types)
ALLOWED_FILE_TYPES = {
    # Images
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    # Videos
    'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/webm',
    # Audio
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/webm',
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'application/zip',
    'application/x-rar-compressed',
}

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_file(file):
    """
    Validate uploaded file for type and size
    """
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise ValueError(f'File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB')
    
    # Check MIME type using python-magic
    file_mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)  # Reset file pointer
    
    if file_mime not in ALLOWED_FILE_TYPES:
        raise ValueError(f'File type {file_mime} is not allowed. Allowed types: images, videos, audio, documents')
    
    return True


def convert_uuids_to_strings(data):
    """
    Recursively convert all UUID objects to strings in a dictionary or list
    """
    if isinstance(data, dict):
        return {key: convert_uuids_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_uuids_to_strings(item) for item in data]
    elif isinstance(data, uuid.UUID):
        return str(data)
    else:
        return data


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        """
        Get conversations for the current user
        """
        user = self.request.user
        queryset = Conversation.objects.filter(
            participants=user
        ).prefetch_related(
            'participants',
            'last_message',
            'last_message__sender'
        ).distinct()
        
        # Filter by unread messages
        unread_only = self.request.query_params.get('unread_only', 'false').lower() == 'true'
        if unread_only:
            queryset = queryset.annotate(
                unread_count=Count(
                    'messages',
                    filter=Q(messages__is_read=False) & ~Q(messages__sender=user)
                )
            ).filter(unread_count__gt=0)
        
        return queryset.order_by('-updated_at')
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create or get existing conversation with another user
        """
        other_user_id = request.data.get('user_id')
        
        if not other_user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if other_user == request.user:
            return Response(
                {'error': 'Cannot create conversation with yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if conversation already exists
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()
        
        if conversation:
            serializer = self.get_serializer(conversation)
            return Response(serializer.data)
        
        # Create new conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get messages for a specific conversation with pagination
        Messages are returned in reverse chronological order (newest first) for infinite scroll
        """
        conversation = self.get_object()
        
        # Check if user is a participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Order by created_at descending (newest first) for reverse infinite scroll
        messages = conversation.messages.select_related('sender').order_by('-created_at')
        
        # Pagination
        paginator = MessagePagination()
        page = paginator.paginate_queryset(messages, request)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            # Reverse the results so oldest is first in each page
            data = list(reversed(serializer.data))
            return paginator.get_paginated_response(data)
        
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Send a message in a conversation
        """
        conversation = self.get_object()
        
        # Check if user is a participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        content = request.data.get('content', '')
        file = request.FILES.get('file')
        file_type = request.data.get('file_type', '')
        
        if not content and not file:
            return Response(
                {'error': 'Message must have content or file'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file if present
        if file:
            try:
                validate_file(file)
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            file=file,
            file_type=file_type
        )
        
        # Update conversation's last message
        conversation.last_message = message
        conversation.save()
        
        serializer = MessageSerializer(message, context={'request': request})
        message_data = convert_uuids_to_strings(serializer.data)
        
        # Broadcast message to WebSocket group for real-time delivery
        channel_layer = get_channel_layer()
        conversation_group_name = f'chat_{conversation.id}'
        
        async_to_sync(channel_layer.group_send)(
            conversation_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )
        
        # Notify all participants about conversation update
        participants = conversation.participants.all()
        for participant in participants:
            async_to_sync(channel_layer.group_send)(
                f'user_{participant.id}',
                {
                    'type': 'conversation_update',
                    'conversation_id': str(conversation.id),
                    'last_message': content or '[File]',
                    'timestamp': message.created_at.isoformat(),
                    'sender_id': str(request.user.id),
                }
            )
        
        return Response(message_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark all messages in a conversation as read
        """
        conversation = self.get_object()
        
        # Check if user is a participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark all unread messages as read
        unread_messages = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user)
        
        for message in unread_messages:
            message.mark_as_read()
        
        return Response({
            'message': 'Messages marked as read',
            'count': unread_messages.count()
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get total unread message count across all conversations
        """
        user = request.user
        total_unread = Message.objects.filter(
            conversation__participants=user,
            is_read=False
        ).exclude(sender=user).count()
        
        return Response({'unread_count': total_unread})
    
    @action(detail=False, methods=['get'])
    def search_friends(self, request):
        """
        Search for friends (with or without existing conversations)
        Useful for starting new conversations
        """
        query = request.query_params.get('q', '').strip()
        
        # Get user's friends
        from accounts.models import Friendship
        friend_ids = Friendship.objects.filter(
            Q(requester=request.user) | Q(receiver=request.user),
            status='accepted'
        ).values_list('requester_id', 'receiver_id')
        
        # Flatten and filter out current user
        all_friend_ids = set()
        for req_id, rec_id in friend_ids:
            if req_id != request.user.id:
                all_friend_ids.add(req_id)
            if rec_id != request.user.id:
                all_friend_ids.add(rec_id)
        
        # Get friends
        friends = User.objects.filter(id__in=all_friend_ids)
        
        # Filter by search query if provided
        if query:
            friends = friends.filter(
                Q(profile_name__icontains=query) | Q(email__icontains=query)
            )
        
        # For each friend, check if conversation exists
        result = []
        for friend in friends:
            conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=friend
            ).first()
            
            result.append({
                'id': friend.id,
                'profile_name': friend.profile_name,
                'email': friend.email,
                'profile_image': request.build_absolute_uri(friend.profile_image.url) if friend.profile_image else None,
                'has_conversation': conversation is not None,
                'conversation_id': str(conversation.id) if conversation else None
            })
        
        return Response(result)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a conversation
        """
        conversation = self.get_object()
        
        # Check if user is a participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """
        Get messages for conversations the user is part of
        """
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a specific message as read
        """
        message = self.get_object()
        
        # Check if user is a participant in the conversation
        if not message.conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Don't mark own messages as read
        if message.sender == request.user:
            return Response(
                {'error': 'Cannot mark own message as read'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.mark_as_read()
        serializer = self.get_serializer(message)
        return Response(serializer.data)


class GlobalChatViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for global chat messages (read-only via REST API)
    Real-time messaging happens through WebSocket
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GlobalChatMessageSerializer
    pagination_class = GlobalChatPagination
    
    def get_queryset(self):
        """
        Get global chat messages ordered newest to oldest for reverse infinite scroll
        """
        return GlobalChatMessage.objects.select_related('sender').order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """
        List global chat messages with pagination
        Messages are reversed within each page so oldest is first
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Reverse the results so oldest is first in each page (consistent with private chat)
            data = list(reversed(serializer.data))
            return self.get_paginated_response(data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """
        Send a message to global chat
        """
        content = request.data.get('content', '')
        file = request.FILES.get('file')
        file_type = request.data.get('file_type', '')
        
        if not content and not file:
            return Response(
                {'error': 'Message must have content or file'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file if present
        if file:
            try:
                validate_file(file)
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        message = GlobalChatMessage.objects.create(
            sender=request.user,
            content=content,
            file=file,
            file_type=file_type
        )
        
        serializer = self.get_serializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CallViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing calls
    Real-time call signaling happens through WebSocket
    This API is for call history
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer
    
    def get_queryset(self):
        """
        Get calls for the authenticated user (either as caller or receiver)
        """
        return Call.objects.filter(
            Q(caller=self.user) | Q(receiver=self.user)
        ).select_related('caller', 'receiver', 'conversation').order_by('-started_at')
    
    @action(detail=False, methods=['get'])
    def conversation_calls(self, request):
        """
        Get call history for a specific conversation
        """
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is participant in the conversation
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        calls = Call.objects.filter(
            conversation=conversation
        ).select_related('caller', 'receiver').order_by('-started_at')
        
        serializer = self.get_serializer(calls, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def end_call(self, request, pk=None):
        """
        End an active call
        """
        call = self.get_object()
        
        # Check if user is participant in the call
        if call.caller != request.user and call.receiver != request.user:
            return Response(
                {'error': 'You are not a participant in this call'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if call is already ended
        if call.status in ['ended', 'rejected', 'missed']:
            return Response(
                {'error': 'Call is already ended'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        call.mark_ended()
        serializer = self.get_serializer(call, context={'request': request})
        return Response(serializer.data)
