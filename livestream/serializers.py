from rest_framework import serializers
from .models import LiveStream, LiveStreamComment, LiveStreamView
from accounts.serializers import UserSerializer


class LiveStreamSerializer(serializers.ModelSerializer):
    """Serializer for viewers - does NOT include stream_key"""
    user = UserSerializer(read_only=True)
    viewer_count = serializers.IntegerField(read_only=True)
    peak_viewers = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = LiveStream
        fields = [
            'id', 'user', 'title', 'description', 'channel_arn', 
            'ingest_endpoint', 'playback_url', 'status',
            'started_at', 'ended_at', 'created_at', 'updated_at',
            'viewer_count', 'peak_viewers'
        ]
        read_only_fields = ['id', 'user', 'channel_arn', 'ingest_endpoint', 
                            'playback_url', 'created_at', 'updated_at']


class LiveStreamOwnerSerializer(serializers.ModelSerializer):
    """Serializer for owner/broadcaster - includes stream_key for broadcasting"""
    user = UserSerializer(read_only=True)
    viewer_count = serializers.IntegerField(read_only=True)
    peak_viewers = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = LiveStream
        fields = [
            'id', 'user', 'title', 'description', 'channel_arn', 
            'stream_key', 'ingest_endpoint', 'playback_url', 'status',
            'started_at', 'ended_at', 'created_at', 'updated_at',
            'viewer_count', 'peak_viewers'
        ]
        read_only_fields = ['id', 'user', 'channel_arn', 'ingest_endpoint', 
                            'playback_url', 'created_at', 'updated_at']


class LiveStreamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveStream
        fields = ['title', 'description']


class LiveStreamCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = LiveStreamComment
        fields = ['id', 'livestream', 'user', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class LiveStreamViewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = LiveStreamView
        fields = ['id', 'livestream', 'user', 'session_id', 'joined_at', 'left_at']
        read_only_fields = ['id', 'user', 'joined_at']


class LiveStreamListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing live streams"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = LiveStream
        fields = [
            'id', 'user', 'title', 'description', 'status', 'playback_url',
            'started_at', 'created_at', 'viewer_count', 'peak_viewers'
        ]
