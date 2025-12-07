from django.contrib import admin
from .models import Conversation, Message, GlobalChatMessage, MessageReadReceipt, Call


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at', 'get_participants']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['participants__profile_name', 'participants__email']
    
    def get_participants(self, obj):
        return ', '.join([p.profile_name for p in obj.participants.all()])
    get_participants.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'conversation', 'content_preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at', 'file_type']
    search_fields = ['sender__profile_name', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] if obj.content else '(No content)'
    content_preview.short_description = 'Content'


@admin.register(GlobalChatMessage)
class GlobalChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'content_preview', 'created_at']
    list_filter = ['created_at', 'file_type']
    search_fields = ['sender__profile_name', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] if obj.content else '(No content)'
    content_preview.short_description = 'Content'


@admin.register(MessageReadReceipt)
class MessageReadReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'conversation', 'last_read_at']
    list_filter = ['last_read_at']
    search_fields = ['user__profile_name']


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['id', 'caller', 'receiver', 'call_type', 'status', 'duration', 'started_at', 'ended_at']
    list_filter = ['call_type', 'status', 'started_at']
    search_fields = ['caller__profile_name', 'receiver__profile_name']
    readonly_fields = ['started_at', 'answered_at', 'ended_at', 'duration']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('caller', 'receiver', 'conversation')
