from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid

User = settings.AUTH_USER_MODEL


# ============== Post Related Models ==============

class Post(models.Model):
    """
    Main post model for user posts
    """
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends'),
        ('private', 'Private'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    society = models.ForeignKey('Society', on_delete=models.CASCADE, related_name='posts', null=True, blank=True)
    
    # Sharing functionality
    shared_post = models.ForeignKey('self', on_delete=models.CASCADE, related_name='shares', null=True, blank=True)
    share_caption = models.TextField(blank=True, help_text='Caption added when sharing a post')

    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='approved')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Post by {self.user} at {self.created_at}"
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def comment_count(self):
        return self.comments.count()
    
    @property
    def share_count(self):
        return self.shares.count()
    
    def is_shared(self):
        """Check if this post is a shared post"""
        return self.shared_post is not None


class PostMedia(models.Model):
    """
    Media attachments for posts (images, videos)
    """
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(
        upload_to='post_media/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi'])]
    )
    caption = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Post Media"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.media_type} for {self.post}"


class PostLike(models.Model):
    """
    Likes on posts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
        indexes = [
            models.Index(fields=['post', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} likes {self.post}"


class Comment(models.Model):
    """
    Comments on posts (no replies)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user} on {self.post}"
    
    @property
    def like_count(self):
        return self.likes.count()


class CommentLike(models.Model):
    """
    Likes on comments
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'comment')
    
    def __str__(self):
        return f"{self.user} likes comment by {self.comment.user}"


# ============== Story Related Models ==============

class Story(models.Model):
    """
    Stories that expire after 24 hours
    """
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends'),
        ('private', 'Private'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    content = models.TextField(blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        verbose_name_plural = "Stories"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_active(self):
        return timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Story by {self.user} at {self.created_at}"


class StoryMedia(models.Model):
    """
    Media attachments for stories
    """
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(
        upload_to='story_media/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi'])]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Story Media"
    
    def __str__(self):
        return f"{self.media_type} for story by {self.story.user}"


class StoryView(models.Model):
    """
    Track who viewed stories
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_views')
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'story')
    
    def __str__(self):
        return f"{self.user} viewed story by {self.story.user}"


# ============== Society Related Models ==============

class Society(models.Model):
    """
    Societies (similar to Facebook groups)
    """
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='society_covers/', blank=True, null=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_societies')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Societies"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.memberships.filter(status='accepted').count()


class SocietyMembership(models.Model):
    """
    User membership in societies
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='society_memberships')
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='memberships')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'society')
    
    def __str__(self):
        return f"{self.user} - {self.society} ({self.role})"


# ============== User Blocking ==============

class UserBlock(models.Model):
    """
    User blocking functionality
    """
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('blocker', 'blocked')
        indexes = [
            models.Index(fields=['blocker']),
            models.Index(fields=['blocked']),
        ]
    
    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


# ============== Notifications ==============

class Notification(models.Model):
    """
    Notifications for various activities
    """
    NOTIFICATION_TYPES = [
        ('friend_request', 'Friend Request'),
        ('friend_accept', 'Friend Accept'),
        ('post_like', 'Post Like'),
        ('post_comment', 'Post Comment'),
        ('post_share', 'Post Share'),
        ('comment_like', 'Comment Like'),
        ('society_invite', 'Society Invite'),
        ('society_join', 'Society Join Request'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    
    # Generic relations to different objects
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    society = models.ForeignKey(Society, on_delete=models.CASCADE, null=True, blank=True)
    
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"Notification for {self.recipient}: {self.notification_type}"
