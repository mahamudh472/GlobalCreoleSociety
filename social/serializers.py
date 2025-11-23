from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import (
    Post, PostMedia, PostLike, Comment, CommentLike,
    Story, StoryMedia, StoryView,
    Society, SocietyMembership,
    Notification
)
from accounts.models import Friendship

User = get_user_model()


# ============== User Serializers ==============

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for nested serialization"""
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'profile_name', 'profile_image']
        read_only_fields = fields
    
    def get_profile_image(self, obj):
        """Return absolute URL for profile image"""
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_image.url)
            # Fallback to BASE_URL when request is not available
            return f"{settings.BASE_URL}{obj.profile_image.url}"
        return None


# ============== Friendship Serializers ==============

class FriendshipSerializer(serializers.ModelSerializer):
    requester = UserBasicSerializer(read_only=True)
    receiver = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Friendship
        fields = ['id', 'requester', 'receiver', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class FriendRequestSerializer(serializers.Serializer):
    """Serializer for sending friend requests"""
    receiver_id = serializers.UUIDField()
    
    def validate_receiver_id(self, value):
        request = self.context.get('request')
        
        # Check if receiver exists
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        
        # Check if trying to send to self
        if str(request.user.id) == str(value):
            raise serializers.ValidationError("You cannot send a friend request to yourself.")
        
        # Check if friendship already exists
        if Friendship.objects.filter(
            requester=request.user, receiver_id=value
        ).exists() or Friendship.objects.filter(
            requester_id=value, receiver=request.user
        ).exists():
            raise serializers.ValidationError("Friend request already exists.")
        
        return value


# ============== Post Serializers ==============

class PostMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    
    class Meta:
        model = PostMedia
        fields = ['id', 'media_type', 'file', 'caption', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_file(self, obj):
        """Return absolute URL for file"""
        if obj.file and hasattr(obj.file, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.file.url)
            # Fallback to BASE_URL when request is not available
            return f"{settings.BASE_URL}{obj.file.url}"
        return None


class CommentSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'content', 'like_count', 'is_liked', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'post', 'created_at', 'updated_at']
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(user=request.user, comment=obj).exists()
        return False


class PostSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    media = PostMediaSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    society = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'privacy', 'society',
            'media', 'like_count', 'comment_count', 'is_liked',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PostLike.objects.filter(user=request.user, post=obj).exists()
        return False
    
    def get_society(self, obj):
        if obj.society:
            return {
                'id': obj.society.id,
                'name': obj.society.name,
                'cover_image': obj.society.cover_image.url if obj.society.cover_image else None,
                'cover_picture': obj.society.cover_image.url if obj.society.cover_image else None,
                'members_count': obj.society.member_count,
            }
        return None


class PostCreateSerializer(serializers.ModelSerializer):
    media_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    media_captions = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Post
        fields = ['content', 'privacy', 'society', 'media_files', 'media_captions']
    
    def validate(self, data):
        # If society is provided, validate user is a member
        society = data.get('society')
        if society:
            request = self.context.get('request')
            if not SocietyMembership.objects.filter(
                user=request.user,
                society=society,
                status='accepted'
            ).exists():
                raise serializers.ValidationError("You must be a member of this society to post.")
        
        return data
    
    def create(self, validated_data):
        media_files = validated_data.pop('media_files', [])
        media_captions = validated_data.pop('media_captions', [])
        
        # Create post
        post = Post.objects.create(**validated_data)
        
        # Create media attachments
        for idx, file in enumerate(media_files):
            caption = media_captions[idx] if idx < len(media_captions) else ''
            
            # Determine media type based on file extension
            file_ext = file.name.split('.')[-1].lower()
            media_type = 'video' if file_ext in ['mp4', 'mov', 'avi'] else 'image'
            
            PostMedia.objects.create(
                post=post,
                media_type=media_type,
                file=file,
                caption=caption
            )
        
        return post


# ============== Society Serializers ==============

class SocietySerializer(serializers.ModelSerializer):
    creator = UserBasicSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    user_membership = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    cover_picture = serializers.ImageField(source='cover_image', read_only=True)
    members_count = serializers.IntegerField(source='member_count', read_only=True)
    
    class Meta:
        model = Society
        fields = [
            'id', 'name', 'description', 'cover_image', 'cover_picture', 'privacy',
            'creator', 'member_count', 'members_count', 'user_membership', 'is_member',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']
    
    def get_user_membership(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = SocietyMembership.objects.filter(
                user=request.user,
                society=obj
            ).first()
            if membership:
                return {
                    'status': membership.status,
                    'role': membership.role
                }
        return None
    
    def get_is_member(self, obj):
        """Check if the current user is a member of this society"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SocietyMembership.objects.filter(
                user=request.user,
                society=obj,
                status='accepted'
            ).exists()
        return False


class SocietyMembershipSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    society = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = SocietyMembership
        fields = ['id', 'user', 'society', 'status', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'society', 'created_at', 'updated_at']


# ============== Story Serializers ==============

class StoryMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryMedia
        fields = ['id', 'media_type', 'file', 'created_at']
        read_only_fields = ['id', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    media = StoryMediaSerializer(many=True, read_only=True)
    view_count = serializers.SerializerMethodField()
    is_viewed = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Story
        fields = [
            'id', 'user', 'content', 'privacy', 'media',
            'view_count', 'is_viewed', 'is_active',
            'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'expires_at']
    
    def get_view_count(self, obj):
        return obj.views.count()
    
    def get_is_viewed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StoryView.objects.filter(user=request.user, story=obj).exists()
        return False
    
    def get_is_active(self, obj):
        return obj.is_active()


class StoryCreateSerializer(serializers.ModelSerializer):
    media_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Story
        fields = ['content', 'privacy', 'media_files']
    
    def create(self, validated_data):
        media_files = validated_data.pop('media_files', [])
        
        # Create story
        story = Story.objects.create(**validated_data)
        
        # Create media attachments
        for file in media_files:
            # Determine media type based on file extension
            file_ext = file.name.split('.')[-1].lower()
            media_type = 'video' if file_ext in ['mp4', 'mov', 'avi'] else 'image'
            
            StoryMedia.objects.create(
                story=story,
                media_type=media_type,
                file=file
            )
        
        return story


# ============== Notification Serializers ==============

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    post_content = serializers.CharField(source='post.content', read_only=True)
    society_name = serializers.CharField(source='society.name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'notification_type', 'message',
            'post', 'post_content', 'comment', 'society', 'society_name',
            'is_read', 'created_at'
        ]
        read_only_fields = fields
