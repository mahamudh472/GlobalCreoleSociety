from rest_framework import serializers
from django.conf import settings
from .models import Conversation, Message, GlobalChatMessage, MessageReadReceipt, Call
from accounts.serializers import UserSimpleSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSimpleSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'file', 'file_url',
            'file_type', 'is_read', 'read_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'created_at', 'updated_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            # Fallback to BASE_URL when request is not available
            return f"{settings.BASE_URL}{obj.file.url}"
        return None


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSimpleSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'other_participant', 'last_message',
            'unread_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user:
            other_user = obj.get_other_participant(request.user)
            if other_user:
                return UserSimpleSerializer(other_user, context={'request': request}).data
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation list"""
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'other_participant', 'last_message',
            'unread_count', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user:
            other_user = obj.get_other_participant(request.user)
            if other_user:
                return UserSimpleSerializer(other_user, context={'request': request}).data
        return None


class GlobalChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSimpleSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = GlobalChatMessage
        fields = [
            'id', 'sender', 'content', 'file', 'file_url',
            'file_type', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            # Fallback to BASE_URL when request is not available
            return f"{settings.BASE_URL}{obj.file.url}"
        return None


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = MessageReadReceipt
        fields = ['id', 'user', 'conversation', 'last_read_message', 'last_read_at']
        read_only_fields = ['id', 'user', 'last_read_at']


class CallSerializer(serializers.ModelSerializer):
    caller = UserSimpleSerializer(read_only=True)
    receiver = UserSimpleSerializer(read_only=True)
    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Call
        fields = [
            'id', 'conversation', 'caller', 'receiver', 'call_type', 'status',
            'started_at', 'answered_at', 'ended_at', 'duration', 'duration_formatted'
        ]
        read_only_fields = ['id', 'caller', 'started_at', 'answered_at', 'ended_at', 'duration']

    def get_duration_formatted(self, obj):
        """Format duration as MM:SS"""
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
