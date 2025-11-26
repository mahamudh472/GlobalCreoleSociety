from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch, Count
from django.utils import timezone

from .models import (
    Post, PostLike, Comment, CommentLike,
    Story, StoryView,
    Society, SocietyMembership,
    Notification, UserBlock
)
from accounts.models import Friendship, User
from .serializers import (
    PostSerializer, PostCreateSerializer, PostShareSerializer, BulkPostShareSerializer, CommentSerializer,
    FriendshipSerializer, FriendRequestSerializer,
    SocietySerializer, SocietyMembershipSerializer,
    StorySerializer, StoryCreateSerializer,
    NotificationSerializer
)
from .permissions import (
    PostPermissions, SocietyPermissions, StoryPermissions,
    get_visible_posts_queryset, get_society_posts_queryset
)


# ============== Custom Pagination Classes ==============

class PostPagination(PageNumberPagination):
    """Pagination for posts feed"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CommentPagination(PageNumberPagination):
    """Pagination for comments"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============== Friend Request Views ==============

class SendFriendRequestView(APIView):
    """Send a friend request to another user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FriendRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            receiver = User.objects.get(id=serializer.validated_data['receiver_id'])
            
            # Create friend request
            friendship = Friendship.objects.create(
                requester=request.user,
                receiver=receiver,
                status='pending'
            )
            
            # Create notification
            Notification.objects.create(
                recipient=receiver,
                sender=request.user,
                notification_type='friend_request',
                message=f"{request.user.profile_name} sent you a friend request"
            )
            
            return Response(
                FriendshipSerializer(friendship).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FriendRequestListView(generics.ListAPIView):
    """List all pending friend requests received by the user"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FriendshipSerializer
    
    def get_queryset(self):
        return Friendship.objects.filter(
            receiver=self.request.user,
            status='pending'
        ).select_related('requester', 'receiver')


class FriendRequestResponseView(APIView):
    """Accept or reject a friend request"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        # Find the friendship where user_id sent request to current user
        friendship = get_object_or_404(
            Friendship,
            requester_id=user_id,
            receiver=request.user,
            status='pending'
        )
        
        action = request.data.get('action')  # 'accept' or 'reject'
        
        if action == 'accept':
            friendship.status = 'accepted'
            friendship.save()
            
            # Create notification
            Notification.objects.create(
                recipient=friendship.requester,
                sender=request.user,
                notification_type='friend_accept',
                message=f"{request.user.profile_name} accepted your friend request"
            )
            
            # Create conversation between the two users
            from chat.models import Conversation, Message
            
            # Check if conversation already exists
            existing_conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=friendship.requester
            ).first()
            
            if not existing_conversation:
                # Create new conversation (without system message)
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, friendship.requester)
            
            return Response(
                FriendshipSerializer(friendship).data,
                status=status.HTTP_200_OK
            )
        elif action == 'reject':
            friendship.delete()
            return Response(
                {"message": "Friend request rejected"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Invalid action. Use 'accept' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )


class FriendListView(generics.ListAPIView):
    """List all friends of the user"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FriendshipSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(
            Q(requester=user, status='accepted') |
            Q(receiver=user, status='accepted')
        ).select_related('requester', 'receiver')


class UnfriendView(APIView):
    """Remove a friend"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, user_id):
        # Find friendship between current user and user_id
        friendship = get_object_or_404(
            Friendship,
            Q(requester=request.user, receiver_id=user_id) |
            Q(requester_id=user_id, receiver=request.user),
            status='accepted'
        )
        
        friendship.delete()
        return Response(
            {"message": "Friend removed successfully"},
            status=status.HTTP_200_OK
        )


class FriendSuggestionsView(APIView):
    """Get suggested users to send friend requests to"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get users who are already friends or have pending requests
        friends_and_pending = Friendship.objects.filter(
            Q(requester=user) | Q(receiver=user)
        ).values_list('requester_id', 'receiver_id')
        
        # Flatten the list and add current user
        excluded_user_ids = set()
        excluded_user_ids.add(user.id)
        for requester_id, receiver_id in friends_and_pending:
            excluded_user_ids.add(requester_id)
            excluded_user_ids.add(receiver_id)
        
        # Get users who blocked current user or current user blocked
        blocked_users = UserBlock.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')
        
        for blocker_id, blocked_id in blocked_users:
            excluded_user_ids.add(blocker_id)
            excluded_user_ids.add(blocked_id)
        
        # Get suggested users (users not in excluded list)
        # Priority: mutual friends, then by recent activity
        suggested_users = User.objects.filter(
            is_active=True
        ).exclude(
            id__in=excluded_user_ids
        ).exclude(
            profile_lock=True  # Exclude private profiles
        ).order_by('-last_login')[:20]  # Limit to 20 suggestions
        
        # Serialize user data
        from accounts.serializers import UserSimpleSerializer
        serializer = UserSimpleSerializer(suggested_users, many=True, context={'request': request})
        
        return Response(serializer.data, status=status.HTTP_200_OK)


# ============== Post Views ==============

class PostCreateView(generics.CreateAPIView):
    """Create a new post"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostCreateSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        # Use the create serializer to validate and create
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(user=request.user)
        
        # Refresh the post with related data
        post = Post.objects.select_related('user', 'society').prefetch_related('media', 'likes', 'comments').get(pk=post.pk)
        
        # Return the full post data using PostSerializer
        post_data = PostSerializer(post, context={'request': request}).data
        headers = self.get_success_headers(post_data)
        return Response(post_data, status=status.HTTP_201_CREATED, headers=headers)


class PostListView(generics.ListAPIView):
    """List posts visible to the user (feed)"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = PostPagination
    
    def get_queryset(self):
        queryset = get_visible_posts_queryset(self.request.user).select_related(
            'user', 'society'
        ).prefetch_related('media', 'likes', 'comments').order_by('-created_at')
        
        # Optional: Filter by specific user
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Optional: Exclude society posts (for profile pages)
        exclude_society = self.request.query_params.get('exclude_society', 'false').lower()
        if exclude_society == 'true':
            queryset = queryset.filter(society__isnull=True)
        
        return queryset


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View, update, or delete a specific post"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    
    def get_queryset(self):
        return Post.objects.select_related('user', 'society').prefetch_related('media')
    
    def get_object(self):
        post = super().get_object()
        
        # Check view permission
        if not PostPermissions.can_view_post(self.request.user, post):
            self.permission_denied(self.request)
        
        return post
    
    def update(self, request, *args, **kwargs):
        post = self.get_object()
        
        if not PostPermissions.can_edit_post(request.user, post):
            return Response(
                {"error": "You don't have permission to edit this post"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        
        if not PostPermissions.can_delete_post(request.user, post):
            return Response(
                {"error": "You don't have permission to delete this post"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class PostLikeView(APIView):
    """Like or unlike a post"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        
        # Check permission
        if not PostPermissions.can_interact_with_post(request.user, post):
            return Response(
                {"error": "You don't have permission to like this post"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Toggle like
        like, created = PostLike.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if not created:
            like.delete()
            return Response(
                {"message": "Post unliked", "liked": False},
                status=status.HTTP_200_OK
            )
        else:
            # Create notification if not liking own post
            if post.user != request.user:
                Notification.objects.create(
                    recipient=post.user,
                    sender=request.user,
                    notification_type='post_like',
                    post=post,
                    message=f"{request.user.profile_name} liked your post"
                )
            
            return Response(
                {"message": "Post liked", "liked": True},
                status=status.HTTP_201_CREATED
            )


class PostShareView(APIView):
    """Share a post with an optional caption"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PostShareSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            post_id = serializer.validated_data['post_id']
            share_caption = serializer.validated_data.get('share_caption', '')
            privacy = serializer.validated_data.get('privacy', 'public')
            society_id = serializer.validated_data.get('society', None)
            
            # Get the original post
            original_post = Post.objects.get(id=post_id)
            
            # Create the shared post
            shared_post = Post.objects.create(
                user=request.user,
                shared_post=original_post,
                share_caption=share_caption,
                privacy=privacy,
                society_id=society_id
            )
            
            # Create notification for the original post owner
            if original_post.user != request.user:
                Notification.objects.create(
                    recipient=original_post.user,
                    sender=request.user,
                    notification_type='post_share',
                    post=original_post,
                    message=f"{request.user.profile_name} shared your post"
                )
            
            # Refresh the shared post with related data
            shared_post = Post.objects.select_related(
                'user', 'society', 'shared_post', 'shared_post__user'
            ).prefetch_related(
                'media', 'likes', 'comments', 'shared_post__media'
            ).get(pk=shared_post.pk)
            
            # Return the full shared post data
            post_data = PostSerializer(shared_post, context={'request': request}).data
            return Response(post_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkPostShareView(APIView):
    """Share a post to multiple users (via messages) and multiple societies"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = BulkPostShareSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            post_id = serializer.validated_data['post_id']
            user_ids = serializer.validated_data.get('user_ids', [])
            society_ids = serializer.validated_data.get('society_ids', [])
            share_caption = serializer.validated_data.get('share_caption', '')
            message_text = serializer.validated_data.get('message_text', '')
            
            # Get the original post
            original_post = Post.objects.get(id=post_id)
            
            # Build the post link (you may need to adjust the base URL)
            from django.conf import settings
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            post_link = f"{base_url}/posts/{original_post.id}/"
            
            results = {
                'messages_sent': [],
                'societies_shared': [],
                'errors': []
            }
            
            # Send messages to users with post link
            if user_ids:
                from chat.models import Conversation, Message
                
                for user_id in user_ids:
                    try:
                        recipient = User.objects.get(id=user_id)
                        
                        # Check if conversation already exists
                        conversation = Conversation.objects.filter(
                            participants=request.user
                        ).filter(
                            participants=recipient
                        ).first()
                        
                        # Create conversation if it doesn't exist
                        if not conversation:
                            conversation = Conversation.objects.create()
                            conversation.participants.add(request.user, recipient)
                        
                        # Create message with post link
                        message_content = message_text if message_text else "Check out this post:"
                        message_content += f"\n\n{post_link}"
                        
                        message = Message.objects.create(
                            conversation=conversation,
                            sender=request.user,
                            content=message_content
                        )
                        
                        # Update conversation's last_message
                        conversation.last_message = message
                        conversation.save(update_fields=['last_message', 'updated_at'])
                        
                        results['messages_sent'].append({
                            'user_id': str(user_id),
                            'user_name': recipient.profile_name,
                            'conversation_id': str(conversation.id),
                            'message_id': str(message.id)
                        })
                        
                    except User.DoesNotExist:
                        results['errors'].append({
                            'user_id': str(user_id),
                            'error': 'User not found'
                        })
                    except Exception as e:
                        results['errors'].append({
                            'user_id': str(user_id),
                            'error': str(e)
                        })
            
            # Share post in societies
            if society_ids:
                for society_id in society_ids:
                    try:
                        society = Society.objects.get(id=society_id)
                        
                        # Check if already shared in this society
                        existing_share = Post.objects.filter(
                            user=request.user,
                            shared_post=original_post,
                            society=society
                        ).first()
                        
                        if existing_share:
                            results['errors'].append({
                                'society_id': str(society_id),
                                'society_name': society.name,
                                'error': 'Post already shared in this society'
                            })
                            continue
                        
                        # Create shared post in society
                        shared_post = Post.objects.create(
                            user=request.user,
                            shared_post=original_post,
                            share_caption=share_caption,
                            privacy='public',  # Society posts are public within the society
                            society=society
                        )
                        
                        results['societies_shared'].append({
                            'society_id': str(society_id),
                            'society_name': society.name,
                            'shared_post_id': str(shared_post.id)
                        })
                        
                    except Society.DoesNotExist:
                        results['errors'].append({
                            'society_id': str(society_id),
                            'error': 'Society not found'
                        })
                    except Exception as e:
                        results['errors'].append({
                            'society_id': str(society_id),
                            'error': str(e)
                        })
            
            # Create notification for the original post owner if any shares were successful
            if (results['messages_sent'] or results['societies_shared']) and original_post.user != request.user:
                Notification.objects.create(
                    recipient=original_post.user,
                    sender=request.user,
                    notification_type='post_share',
                    post=original_post,
                    message=f"{request.user.profile_name} shared your post"
                )
            
            # Determine response status
            if results['errors'] and not (results['messages_sent'] or results['societies_shared']):
                # All operations failed
                return Response(results, status=status.HTTP_400_BAD_REQUEST)
            elif results['errors']:
                # Partial success
                return Response(results, status=status.HTTP_207_MULTI_STATUS)
            else:
                # Complete success
                return Response(results, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostCommentListView(generics.ListCreateAPIView):
    """List or create comments on a post"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    pagination_class = CommentPagination
    
    def get_queryset(self):
        post_id = self.kwargs['pk']
        post = get_object_or_404(Post, id=post_id)
        
        # Check permission
        if not PostPermissions.can_view_post(self.request.user, post):
            return Comment.objects.none()
        
        return Comment.objects.filter(post=post).select_related('user').prefetch_related('likes').order_by('created_at')
    
    def perform_create(self, serializer):
        post_id = self.kwargs['pk']
        post = get_object_or_404(Post, id=post_id)
        
        # Check permission
        if not PostPermissions.can_interact_with_post(self.request.user, post):
            return Response(
                {"error": "You don't have permission to comment on this post"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment = serializer.save(user=self.request.user, post=post)
        
        # Create notification if not commenting on own post
        if post.user != self.request.user:
            Notification.objects.create(
                recipient=post.user,
                sender=self.request.user,
                notification_type='post_comment',
                post=post,
                comment=comment,
                message=f"{self.request.user.profile_name} commented on your post"
            )


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View, update, or delete a comment"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    queryset = Comment.objects.select_related('user', 'post')
    
    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        
        if comment.user != request.user:
            return Response(
                {"error": "You don't have permission to edit this comment"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        
        # Can delete own comment or if post owner or society moderator
        can_delete = (
            comment.user == request.user or
            comment.post.user == request.user or
            (comment.post.society and SocietyPermissions.can_moderate_society(
                request.user, comment.post.society
            ))
        )
        
        if not can_delete:
            return Response(
                {"error": "You don't have permission to delete this comment"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class CommentLikeView(APIView):
    """Like or unlike a comment"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        comment = get_object_or_404(Comment, id=pk)
        
        # Check if user can view the post
        if not PostPermissions.can_view_post(request.user, comment.post):
            return Response(
                {"error": "You don't have permission to like this comment"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Toggle like
        like, created = CommentLike.objects.get_or_create(
            user=request.user,
            comment=comment
        )
        
        if not created:
            like.delete()
            return Response(
                {"message": "Comment unliked", "liked": False},
                status=status.HTTP_200_OK
            )
        else:
            # Create notification if not liking own comment
            if comment.user != request.user:
                Notification.objects.create(
                    recipient=comment.user,
                    sender=request.user,
                    notification_type='comment_like',
                    comment=comment,
                    message=f"{request.user.profile_name} liked your comment"
                )
            
            return Response(
                {"message": "Comment liked", "liked": True},
                status=status.HTTP_201_CREATED
            )


# ============== Society Views ==============

class SocietyListView(generics.ListAPIView):
    """List societies with optional filtering
    
    Query Parameters:
    - my_societies=true: Returns only societies user is a member of
    - available=true: Returns only societies user is NOT a member of (available to join)
    - (no params): Returns both user's societies and public societies
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SocietySerializer
    
    def get_queryset(self):
        user = self.request.user
        my_societies = self.request.query_params.get('my_societies', None)
        available = self.request.query_params.get('available', None)
        
        # Get societies user is a member of
        user_society_ids = SocietyMembership.objects.filter(
            user=user,
            status='accepted'
        ).values_list('society_id', flat=True)
        
        # Filter based on query parameters
        if my_societies == 'true':
            # Return only societies user is a member of
            return Society.objects.filter(
                id__in=user_society_ids
            ).select_related('creator').prefetch_related('memberships').distinct()
        elif available == 'true':
            # Return only societies user is NOT a member of (available to join)
            return Society.objects.filter(
                Q(privacy='public') & ~Q(id__in=user_society_ids)
            ).select_related('creator').prefetch_related('memberships').distinct()
        else:
            # Default: Return both user's societies and public societies
            return Society.objects.filter(
                Q(id__in=user_society_ids) | Q(privacy='public')
            ).select_related('creator').prefetch_related('memberships').distinct()


class SocietyCreateView(generics.CreateAPIView):
    """Create a new society"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SocietySerializer
    
    def perform_create(self, serializer):
        society = serializer.save(creator=self.request.user)
        
        # Auto-add creator as admin member
        SocietyMembership.objects.create(
            user=self.request.user,
            society=society,
            status='accepted',
            role='admin'
        )


class SocietyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View, update, or delete a society"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SocietySerializer
    queryset = Society.objects.select_related('creator')
    
    def get_object(self):
        society = super().get_object()
        
        # Check view permission
        if not SocietyPermissions.can_view_society(self.request.user, society):
            self.permission_denied(self.request)
        
        return society
    
    def update(self, request, *args, **kwargs):
        society = self.get_object()
        
        if not SocietyPermissions.can_manage_society(request.user, society):
            return Response(
                {"error": "You don't have permission to manage this society"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        society = self.get_object()
        
        if not SocietyPermissions.is_society_creator(request.user, society):
            return Response(
                {"error": "Only the creator can delete this society"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class SocietyJoinView(APIView):
    """Join a society (request to join for private societies)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        society = get_object_or_404(Society, id=pk)
        
        # Check if already a member
        if SocietyMembership.objects.filter(
            user=request.user, society=society
        ).exists():
            return Response(
                {"error": "You are already a member or have a pending request"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create membership
        if society.privacy == 'public':
            membership = SocietyMembership.objects.create(
                user=request.user,
                society=society,
                status='accepted',
                role='member'
            )
            message = "Joined society successfully"
        else:
            membership = SocietyMembership.objects.create(
                user=request.user,
                society=society,
                status='pending',
                role='member'
            )
            message = "Join request sent"
            
            # Notify admins
            admins = User.objects.filter(
                society_memberships__society=society,
                society_memberships__role='admin',
                society_memberships__status='accepted'
            )
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    sender=request.user,
                    notification_type='society_join',
                    society=society,
                    message=f"{request.user.profile_name} wants to join {society.name}"
                )
        
        return Response(
            SocietyMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED
        )


class SocietyLeaveView(APIView):
    """Leave a society"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, pk):
        society = get_object_or_404(Society, id=pk)
        
        membership = get_object_or_404(
            SocietyMembership,
            user=request.user,
            society=society
        )
        
        # Cannot leave if creator (must delete society instead)
        if society.creator == request.user:
            return Response(
                {"error": "Creator cannot leave. Delete the society instead."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.delete()
        return Response(
            {"message": "Left society successfully"},
            status=status.HTTP_200_OK
        )


class SocietyMemberListView(generics.ListAPIView):
    """List members of a society"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SocietyMembershipSerializer
    
    def get_queryset(self):
        society_id = self.kwargs['pk']
        society = get_object_or_404(Society, id=society_id)
        
        # Check view permission
        if not SocietyPermissions.can_view_society(self.request.user, society):
            return SocietyMembership.objects.none()
        
        return SocietyMembership.objects.filter(
            society=society,
            status='accepted'
        ).select_related('user')


class SocietyPostListView(generics.ListAPIView):
    """List posts in a society"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    
    def get_queryset(self):
        society_id = self.kwargs['pk']
        society = get_object_or_404(Society, id=society_id)
        
        return get_society_posts_queryset(
            self.request.user, society
        ).select_related('user', 'society').prefetch_related('media')


# ============== Story Views ==============

class StoryListView(generics.ListAPIView):
    """List active stories from friends"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StorySerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Get friends
        friends = User.objects.filter(
            Q(friend_requests_sent__receiver=user, friend_requests_sent__status='accepted') |
            Q(friend_requests_received__requester=user, friend_requests_received__status='accepted')
        ).distinct()
        
        # Get blocked users
        blocked_users = User.objects.filter(blocked_by__blocker=user)
        users_who_blocked = User.objects.filter(blocking__blocked=user)
        
        # Get active stories
        return Story.objects.filter(
            Q(user__in=friends, privacy__in=['public', 'friends']) |
            Q(user=user) |
            Q(privacy='public')
        ).filter(
            expires_at__gt=timezone.now()
        ).exclude(
            user__in=blocked_users
        ).exclude(
            user__in=users_who_blocked
        ).select_related('user').prefetch_related('media').distinct()


class StoryCreateView(generics.CreateAPIView):
    """Create a new story"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StoryCreateSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StoryDetailView(generics.RetrieveDestroyAPIView):
    """View or delete a story"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StorySerializer
    queryset = Story.objects.select_related('user').prefetch_related('media')
    
    def get_object(self):
        story = super().get_object()
        
        # Check view permission
        if not StoryPermissions.can_view_story(self.request.user, story):
            self.permission_denied(self.request)
        
        # Record view
        if story.user != self.request.user:
            StoryView.objects.get_or_create(
                user=self.request.user,
                story=story
            )
        
        return story
    
    def destroy(self, request, *args, **kwargs):
        story = self.get_object()
        
        if story.user != request.user:
            return Response(
                {"error": "You can only delete your own stories"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


# ============== Notification Views ==============

class NotificationListView(generics.ListAPIView):
    """List user's notifications"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('sender', 'post', 'comment', 'society')


class NotificationMarkReadView(APIView):
    """Mark notification(s) as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        notification_ids = request.data.get('notification_ids', [])
        
        if notification_ids:
            Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user
            ).update(is_read=True)
        else:
            # Mark all as read
            Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).update(is_read=True)
        
        return Response(
            {"message": "Notifications marked as read"},
            status=status.HTTP_200_OK
        )


# ============== User Blocking Views ==============

class BlockUserView(APIView):
    """Block a user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        user_to_block = get_object_or_404(User, id=pk)
        
        if user_to_block == request.user:
            return Response(
                {"error": "You cannot block yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        block, created = UserBlock.objects.get_or_create(
            blocker=request.user,
            blocked=user_to_block
        )
        
        if not created:
            return Response(
                {"message": "User already blocked"},
                status=status.HTTP_200_OK
            )
        
        # Remove friendship if exists
        Friendship.objects.filter(
            Q(requester=request.user, receiver=user_to_block) |
            Q(requester=user_to_block, receiver=request.user)
        ).delete()
        
        return Response(
            {"message": "User blocked successfully"},
            status=status.HTTP_201_CREATED
        )


class UnblockUserView(APIView):
    """Unblock a user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, pk):
        user_to_unblock = get_object_or_404(User, id=pk)
        
        block = get_object_or_404(
            UserBlock,
            blocker=request.user,
            blocked=user_to_unblock
        )
        
        block.delete()
        return Response(
            {"message": "User unblocked successfully"},
            status=status.HTTP_200_OK
        )
