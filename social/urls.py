from django.urls import path
from .views import (
    # Friend request views
    ApproveMembershipRequestView, SendFriendRequestView, FriendRequestListView, FriendRequestResponseView,
    FriendListView, UnfriendView, FriendSuggestionsView, FriendshipStatusView,
    
    # Post views
    PostCreateView, PostListView, PostDetailView, PostLikeView, PostShareView, BulkPostShareView,
    PostCommentListView, CommentDetailView, CommentLikeView,
    
    # Society views
    SocietyListView, SocietyCreateView, SocietyDetailView,
    SocietyJoinView, SocietyLeaveView, SocietyMemberListView, SocietyPostListView,
    ApproveMembershipRequestView, RejectPostView, ApprovePostView, PendingPostsView, PendingMembershipRequestsView,
    
    # Story views
    StoryListView, StoryCreateView, StoryDetailView,
    
    # Notification views
    NotificationListView, NotificationMarkReadView, DeleteNotificationView,
    
    # User blocking views
    BlockUserView, UnblockUserView, BlockListView,
)

urlpatterns = [
    # ============== Friend Requests ==============
    path('friends/request/', SendFriendRequestView.as_view(), name='send-friend-request'),
    path('friends/requests/', FriendRequestListView.as_view(), name='friend-request-list'),
    path('friends/requests/<uuid:user_id>/response/', FriendRequestResponseView.as_view(), name='friend-request-response'),
    path('friends/', FriendListView.as_view(), name='friend-list'),
    path('friends/<uuid:user_id>/unfriend/', UnfriendView.as_view(), name='unfriend'),
    path('friends/suggestions/', FriendSuggestionsView.as_view(), name='friend-suggestions'),
    path('friends/status/<uuid:user_id>/', FriendshipStatusView.as_view(), name='friendship-status'),
    
    # ============== Posts ==============
    path('posts/', PostListView.as_view(), name='post-list'),
    path('posts/create/', PostCreateView.as_view(), name='post-create'),
    path('posts/share/', PostShareView.as_view(), name='post-share'),
    path('posts/share-bulk/', BulkPostShareView.as_view(), name='post-share-bulk'),
    path('posts/<uuid:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<uuid:pk>/like/', PostLikeView.as_view(), name='post-like'),
    path('posts/<uuid:pk>/comments/', PostCommentListView.as_view(), name='post-comments'),
    
    # ============== Comments ==============
    path('comments/<uuid:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    path('comments/<uuid:pk>/like/', CommentLikeView.as_view(), name='comment-like'),
    
    # ============== Societies ==============
    path('societies/', SocietyListView.as_view(), name='society-list'),
    path('societies/create/', SocietyCreateView.as_view(), name='society-create'),
    path('societies/<uuid:pk>/', SocietyDetailView.as_view(), name='society-detail'),
    path('societies/<uuid:pk>/join/', SocietyJoinView.as_view(), name='society-join'),
    path('societies/<uuid:pk>/leave/', SocietyLeaveView.as_view(), name='society-leave'),
    path('societies/<uuid:pk>/members/', SocietyMemberListView.as_view(), name='society-members'),
    path('societies/<uuid:pk>/posts/', SocietyPostListView.as_view(), name='society-posts'),
    path('societies/<uuid:society_pk>/memberships/<int:membership_pk>/approve/', ApproveMembershipRequestView.as_view(), name='approve-membership-request'),
    path('posts/<uuid:pk>/approve/', ApprovePostView.as_view(), name='approve-post'),
    path('posts/<uuid:pk>/reject/', RejectPostView.as_view(), name='reject-post'),
    path('societies/<uuid:pk>/pending-posts/', PendingPostsView.as_view(), name='pending-posts'),
    path('societies/<uuid:pk>/pending-membership-requests/', PendingMembershipRequestsView.as_view(), name='pending-membership-requests'),

    
    # ============== Stories ==============
    path('stories/', StoryListView.as_view(), name='story-list'),
    path('stories/create/', StoryCreateView.as_view(), name='story-create'),
    path('stories/<uuid:pk>/', StoryDetailView.as_view(), name='story-detail'),
    
    # ============== Notifications ==============
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/mark-read/<uuid:pk>/', NotificationMarkReadView.as_view(), name='notification-mark-read-single'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/delete/<uuid:pk>/', DeleteNotificationView.as_view(), name='notification-delete-single'),
    
    # ============== User Blocking ==============
    path('users/<uuid:pk>/block/', BlockUserView.as_view(), name='block-user'),
    path('users/<uuid:pk>/unblock/', UnblockUserView.as_view(), name='unblock-user'),
    path('users/blocked/', BlockListView.as_view(), name='blocked-user-list'),
]
