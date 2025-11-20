from django.contrib import admin
from .models import (
    Post, PostMedia, PostLike, Comment, CommentLike,
    Story, StoryMedia, StoryView,
    Society, SocietyMembership,
    UserBlock, Notification
)


# ============== Post Admin ==============

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_preview', 'privacy', 'society', 'created_at', 'like_count', 'comment_count')
    list_filter = ('privacy', 'created_at', 'society')
    search_fields = ('user__email', 'user__profile_name', 'content')
    date_hierarchy = 'created_at'
    inlines = [PostMediaInline]
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__profile_name')
    date_hierarchy = 'created_at'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'content_preview', 'created_at', 'like_count')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__profile_name', 'content')
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__profile_name')
    date_hierarchy = 'created_at'


# ============== Story Admin ==============

class StoryMediaInline(admin.TabularInline):
    model = StoryMedia
    extra = 0


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_preview', 'privacy', 'created_at', 'expires_at', 'is_active')
    list_filter = ('privacy', 'created_at')
    search_fields = ('user__email', 'user__profile_name', 'content')
    date_hierarchy = 'created_at'
    inlines = [StoryMediaInline]
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'story', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__email', 'user__profile_name')
    date_hierarchy = 'viewed_at'


# ============== Society Admin ==============

@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'privacy', 'created_at', 'member_count')
    list_filter = ('privacy', 'created_at')
    search_fields = ('name', 'description', 'creator__email')
    date_hierarchy = 'created_at'


@admin.register(SocietyMembership)
class SocietyMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'society', 'role', 'status', 'created_at')
    list_filter = ('role', 'status', 'created_at')
    search_fields = ('user__email', 'user__profile_name', 'society__name')
    date_hierarchy = 'created_at'


# ============== User Block Admin ==============

@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__email', 'blocked__email', 'blocker__profile_name', 'blocked__profile_name')
    date_hierarchy = 'created_at'


# ============== Notification Admin ==============

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sender', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'sender__email', 'message')
    date_hierarchy = 'created_at'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
