from django.db import models
from django.conf import settings
import uuid

User = settings.AUTH_USER_MODEL


class LiveStream(models.Model):
    """
    Model for managing live streams
    """
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('live', 'Live'),
        ('ended', 'Ended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livestreams')
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    
    # AWS IVS specific fields
    channel_arn = models.CharField(max_length=255, blank=True)
    stream_key = models.CharField(max_length=255, blank=True)
    ingest_endpoint = models.CharField(max_length=255, blank=True)
    playback_url = models.CharField(max_length=500, blank=True)
    
    # Stream status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    viewer_count = models.IntegerField(default=0)
    peak_viewers = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"LiveStream by {self.user} - {self.title or 'Untitled'}"


class LiveStreamComment(models.Model):
    """
    Comments for live streams (real-time)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    livestream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livestream_comments')
    comment = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['livestream', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user} on {self.livestream}"


class LiveStreamView(models.Model):
    """
    Track viewers for live streams
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    livestream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livestream_views', null=True, blank=True)
    
    # For tracking anonymous viewers
    session_id = models.CharField(max_length=255, blank=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['livestream', '-joined_at']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else f"Anonymous ({self.session_id[:8]})"
        return f"{username} viewing {self.livestream}"
