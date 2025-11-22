from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet, GlobalChatViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'global-chat', GlobalChatViewSet, basename='global-chat')

urlpatterns = [
    path('', include(router.urls)),
]
