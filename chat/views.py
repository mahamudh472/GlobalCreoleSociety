from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Count, Max, Prefetch
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import Conversation, Message, GlobalChatMessage, MessageReadReceipt
from .serializers import (
    ConversationSerializer, ConversationListSerializer,
    MessageSerializer, GlobalChatMessageSerializer,
    MessageReadReceiptSerializer
)

User = get_user_model()


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
        Get messages for a specific conversation
        """
        conversation = self.get_object()
        
        # Check if user is a participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = conversation.messages.select_related('sender').order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
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
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
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
    
    def get_queryset(self):
        """
        Get global chat messages
        """
        return GlobalChatMessage.objects.select_related('sender').order_by('-created_at')
    
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
        
        message = GlobalChatMessage.objects.create(
            sender=request.user,
            content=content,
            file=file,
            file_type=file_type
        )
        
        serializer = self.get_serializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
