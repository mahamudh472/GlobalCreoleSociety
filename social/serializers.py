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
    share_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    society = serializers.SerializerMethodField()
    shared_post = serializers.SerializerMethodField()
    is_shared = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'privacy', 'society',
            'media', 'like_count', 'comment_count', 'share_count', 'is_liked',
            'shared_post', 'share_caption', 'is_shared',
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
            # Use members_count annotation if available, otherwise count manually
            members_count = getattr(obj.society, 'members_count', None)
            if members_count is None:
                members_count = obj.society.memberships.filter(status='accepted').count()
            
            return {
                'id': obj.society.id,
                'name': obj.society.name,
                'cover_image': self.context.get('request').build_absolute_uri(obj.society.cover_image.url) if obj.society.cover_image else None,
                'background_image': self.context.get('request').build_absolute_uri(obj.society.background_image.url) if obj.society.background_image else None,
                'profile_image': self.context.get('request').build_absolute_uri(obj.society.profile_image.url) if obj.society.profile_image else None,
                'members_count': members_count,
            }
        return None
    
    def get_share_count(self, obj):
        """Get count of times this post has been shared"""
        return obj.shares.count()
    
    def get_shared_post(self, obj):
        """Return the original shared post if this is a share"""
        if obj.shared_post:
            # Prevent infinite recursion by excluding shared_post field in nested serialization
            return {
                'id': obj.shared_post.id,
                'user': UserBasicSerializer(obj.shared_post.user, context=self.context).data,
                'content': obj.shared_post.content,
                'privacy': obj.shared_post.privacy,
                'media': PostMediaSerializer(obj.shared_post.media.all(), many=True, context=self.context).data,
                'like_count': obj.shared_post.like_count,
                'comment_count': obj.shared_post.comment_count,
                'share_count': obj.shared_post.shares.count(),
                'created_at': obj.shared_post.created_at,
                'updated_at': obj.shared_post.updated_at,
            }
        return None
    
    def get_is_shared(self, obj):
        """Check if this post is a shared post"""
        return obj.shared_post is not None


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


class PostShareSerializer(serializers.Serializer):
    """Serializer for sharing a post"""
    post_id = serializers.UUIDField(required=True, help_text="ID of the post to share")
    share_caption = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="Optional caption for the shared post"
    )
    privacy = serializers.ChoiceField(
        choices=Post.PRIVACY_CHOICES,
        default='public',
        help_text="Privacy setting for the shared post"
    )
    society = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional society to share the post in"
    )
    
    def validate_post_id(self, value):
        """Validate that the post exists and can be shared"""
        try:
            post = Post.objects.get(id=value)
        except Post.DoesNotExist:
            raise serializers.ValidationError("Post not found.")
        
        # Check if post is already a shared post (prevent recursive sharing)
        if post.shared_post:
            raise serializers.ValidationError("You cannot share a post that is already a share. Share the original post instead.")
        
        return value
    
    def validate_society(self, value):
        """Validate society membership if sharing to a society"""
        if value:
            request = self.context.get('request')
            if not SocietyMembership.objects.filter(
                user=request.user,
                society_id=value,
                status='accepted'
            ).exists():
                raise serializers.ValidationError("You must be a member of this society to share posts there.")
        return value
    
    def validate(self, data):
        """Additional validation"""
        request = self.context.get('request')
        post_id = data.get('post_id')
        
        # Check if user already shared this post
        if Post.objects.filter(user=request.user, shared_post_id=post_id).exists():
            raise serializers.ValidationError("You have already shared this post.")
        
        # Get the post and check view permissions
        post = Post.objects.get(id=post_id)
        from .permissions import PostPermissions
        if not PostPermissions.can_view_post(request.user, post):
            raise serializers.ValidationError("You don't have permission to share this post.")
        
        return data


class BulkPostShareSerializer(serializers.Serializer):
    """Serializer for sharing a post to multiple users and societies"""
    post_id = serializers.UUIDField(required=True, help_text="ID of the post to share")
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="List of user IDs to send the post link via message"
    )
    society_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="List of society IDs to share the post in"
    )
    share_caption = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional caption for the shared posts in societies"
    )
    message_text = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional message text to send with the post link to users"
    )
    
    def validate_post_id(self, value):
        """Validate that the post exists and can be shared"""
        try:
            post = Post.objects.get(id=value)
        except Post.DoesNotExist:
            raise serializers.ValidationError("Post not found.")
        
        # Check if post is already a shared post (prevent recursive sharing)
        if post.shared_post:
            raise serializers.ValidationError("You cannot share a post that is already a share. Share the original post instead.")
        
        return value
    
    def validate_user_ids(self, value):
        """Validate that all user IDs exist"""
        if value:
            existing_users = User.objects.filter(id__in=value).values_list('id', flat=True)
            existing_users_set = set(str(uid) for uid in existing_users)
            provided_users_set = set(str(uid) for uid in value)
            
            missing_users = provided_users_set - existing_users_set
            if missing_users:
                raise serializers.ValidationError(
                    f"The following user IDs do not exist: {', '.join(missing_users)}"
                )
        return value
    
    def validate_society_ids(self, value):
        """Validate society IDs and membership"""
        if value:
            request = self.context.get('request')
            
            # Check if all societies exist
            existing_societies = Society.objects.filter(id__in=value).values_list('id', flat=True)
            existing_societies_set = set(str(sid) for sid in existing_societies)
            provided_societies_set = set(str(sid) for sid in value)
            
            missing_societies = provided_societies_set - existing_societies_set
            if missing_societies:
                raise serializers.ValidationError(
                    f"The following society IDs do not exist: {', '.join(missing_societies)}"
                )
            
            # Check if user is a member of all societies
            user_societies = SocietyMembership.objects.filter(
                user=request.user,
                society_id__in=value,
                status='accepted'
            ).values_list('society_id', flat=True)
            user_societies_set = set(str(sid) for sid in user_societies)
            
            non_member_societies = provided_societies_set - user_societies_set
            if non_member_societies:
                raise serializers.ValidationError(
                    f"You are not a member of the following societies: {', '.join(non_member_societies)}"
                )
        
        return value
    
    def validate(self, data):
        """Additional validation"""
        request = self.context.get('request')
        post_id = data.get('post_id')
        user_ids = data.get('user_ids', [])
        society_ids = data.get('society_ids', [])
        
        # At least one of user_ids or society_ids must be provided
        if not user_ids and not society_ids:
            raise serializers.ValidationError(
                "You must provide at least one user_id or society_id to share the post."
            )
        
        # Get the post and check view permissions
        post = Post.objects.get(id=post_id)
        from .permissions import PostPermissions
        if not PostPermissions.can_view_post(request.user, post):
            raise serializers.ValidationError("You don't have permission to share this post.")
        
        # Check if user is trying to send to themselves
        if str(request.user.id) in [str(uid) for uid in user_ids]:
            raise serializers.ValidationError("You cannot send the post link to yourself.")
        
        return data


# ============== Society Serializers ==============

class SocietySerializer(serializers.ModelSerializer):
    creator = UserBasicSerializer(read_only=True)
    members_count = serializers.IntegerField(read_only=True)
    pending_posts_count = serializers.IntegerField(read_only=True, required=False)
    pending_members_count = serializers.IntegerField(read_only=True, required=False)
    user_membership = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    media_count = serializers.SerializerMethodField()
    post_count = serializers.IntegerField(source='posts.count', read_only=True)
    
    # Read-only URL fields for image display
    profile_image_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    background_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Society
        fields = [
            'id', 'name', 'description', 'profile_image', 'cover_image', 'background_image', 
            'profile_image_url', 'cover_image_url', 'background_image_url', 'privacy',
            'creator', 'members_count', 'user_membership', 'is_member', 'media_count', 'post_count', 
            'pending_posts_count', 'pending_members_count',
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
    
    def get_media_count(self, obj):
        """Get count of media posts in the society"""
        return PostMedia.objects.filter(post__society=obj).count()
    
    def get_profile_image_url(self, obj):
        """Return absolute URL for profile image"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return f"{settings.BASE_URL}{obj.profile_image.url}"
        return None
    
    def get_cover_image_url(self, obj):
        """Return absolute URL for cover image"""
        if obj.cover_image and hasattr(obj.cover_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.cover_image.url)
            # Fallback to BASE_URL when request is not available
            return f"{settings.BASE_URL}{obj.cover_image.url}"
        return None
    
    def get_background_image_url(self, obj):
        """Return absolute URL for background image"""
        if obj.background_image and hasattr(obj.background_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.background_image.url)
            # Fallback to BASE_URL when request is not available
            return f"{settings.BASE_URL}{obj.background_image.url}"
        return None


class SocietyMembershipSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    society = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = SocietyMembership
        fields = ['id', 'user', 'society', 'status', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'society', 'created_at', 'updated_at']


# ============== Story Serializers ==============

class StoryMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    
    class Meta:
        model = StoryMedia
        fields = ['id', 'media_type', 'file', 'created_at']
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


# ============== Advertisement Serializers ==============

from .models import Advertisement, AdvertisementMedia

class AdvertisementMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AdvertisementMedia
        fields = ['id', 'media_type', 'file', 'file_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.file.url)
            return f"{settings.BASE_URL}{obj.file.url}"
        return None


class AdvertisementSerializer(serializers.ModelSerializer):
    media = AdvertisementMediaSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Advertisement
        fields = [
            'id', 'company_name', 'email', 'country_code', 'phone_number',
            'owner_name', 'title', 'description', 'duration_days', 'price_per_day',
            'agree_to_share', 'status', 'total_price', 'media', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class AdvertisementCreateSerializer(serializers.ModelSerializer):
    media_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Advertisement
        fields = [
            'company_name', 'email', 'country_code', 'phone_number',
            'owner_name', 'title', 'description', 'duration_days', 'price_per_day',
            'agree_to_share', 'media_files'
        ]
    
    def validate_duration_days(self, value):
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day.")
        if value > 365:
            raise serializers.ValidationError("Duration cannot exceed 365 days.")
        return value
    
    def validate_price_per_day(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value
    
    def create(self, validated_data):
        media_files = validated_data.pop('media_files', [])
        
        # Get user if authenticated
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        advertisement = Advertisement.objects.create(**validated_data)
        
        # Create media files
        for file in media_files:
            file_ext = file.name.split('.')[-1].lower()
            media_type = 'video' if file_ext in ['mp4', 'mov', 'avi'] else 'image'
            
            AdvertisementMedia.objects.create(
                advertisement=advertisement,
                media_type=media_type,
                file=file
            )
        
        return advertisement
