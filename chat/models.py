from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Conversation(models.Model):
    """
    Model to represent a conversation between two users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        participants = self.participants.all()[:2]
        return f"Conversation between {', '.join([p.profile_name for p in participants])}"

    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        return self.participants.exclude(id=user.id).first()

    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    """
    Model to represent a message in a conversation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/', blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True)  # image, video, document, etc.
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.profile_name} at {self.created_at}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class GlobalChatMessage(models.Model):
    """
    Model to represent messages in the global chat room.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='global_messages'
    )
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='global_chat_files/%Y/%m/%d/', blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True)  # image, video, document, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Global message from {self.sender.profile_name} at {self.created_at}"


class MessageReadReceipt(models.Model):
    """
    Track when each user reads messages in a conversation.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    last_read_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'conversation')

    def __str__(self):
        return f"{self.user.profile_name} read receipt for conversation {self.conversation.id}"


class Call(models.Model):
    """
    Model to represent audio/video calls between users.
    """
    CALL_TYPE_CHOICES = [
        ('audio', 'Audio Call'),
        ('video', 'Video Call'),
    ]
    
    CALL_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('ringing', 'Ringing'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
        ('ended', 'Ended'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='calls'
    )
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_calls'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_calls'
    )
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES, default='audio')
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='initiated')
    started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Call duration in seconds")
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.call_type.title()} call from {self.caller.profile_name} to {self.receiver.profile_name}"
    
    def mark_accepted(self):
        """Mark call as accepted"""
        self.status = 'accepted'
        self.answered_at = timezone.now()
        self.save(update_fields=['status', 'answered_at'])
    
    def mark_ended(self):
        """Mark call as ended and calculate duration"""
        self.status = 'ended'
        self.ended_at = timezone.now()
        if self.answered_at:
            self.duration = int((self.ended_at - self.answered_at).total_seconds())
        self.save(update_fields=['status', 'ended_at', 'duration'])
    
    def mark_rejected(self):
        """Mark call as rejected"""
        self.status = 'rejected'
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'ended_at'])
    
    def mark_missed(self):
        """Mark call as missed"""
        self.status = 'missed'
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'ended_at'])
