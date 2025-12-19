from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiveStreamViewSet, LiveStreamCommentViewSet, LiveStreamViewViewSet

router = DefaultRouter()
router.register(r'streams', LiveStreamViewSet, basename='livestream')
router.register(r'comments', LiveStreamCommentViewSet, basename='livestream-comment')
router.register(r'views', LiveStreamViewViewSet, basename='livestream-view')

urlpatterns = [
    path('', include(router.urls)),
]
