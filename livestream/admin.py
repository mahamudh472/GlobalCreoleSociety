from django.contrib import admin
from .models import LiveStream, LiveStreamComment, LiveStreamView


@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'status', 'viewer_count', 'peak_viewers', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'channel_arn', 'playback_url']


@admin.register(LiveStreamComment)
class LiveStreamCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'livestream', 'user', 'comment', 'created_at']
    list_filter = ['created_at']
    search_fields = ['comment', 'user__username']
    readonly_fields = ['id', 'created_at']


@admin.register(LiveStreamView)
class LiveStreamViewAdmin(admin.ModelAdmin):
    list_display = ['id', 'livestream', 'user', 'session_id', 'joined_at', 'left_at']
    list_filter = ['joined_at']
    search_fields = ['user__username', 'session_id']
    readonly_fields = ['id', 'joined_at']
