"""
Permission helpers for social media functionality
"""
from django.db.models import Q
from .models import SocietyMembership, UserBlock, Friendship


class SocietyPermissions:
    """
    Helper class to check society-related permissions
    """
    
    @staticmethod
    def can_view_society(user, society):
        """
        Check if user can view a society
        - Public societies: everyone can view
        - Private societies: only members can view
        """
        if society.privacy == 'public':
            return True
        
        # Check if user is a member
        return SocietyMembership.objects.filter(
            user=user,
            society=society,
            status='accepted'
        ).exists()
    
    @staticmethod
    def can_post_in_society(user, society):
        """
        Check if user can create posts in a society
        Only accepted members can post
        """
        return SocietyMembership.objects.filter(
            user=user,
            society=society,
            status='accepted'
        ).exists()
    
    @staticmethod
    def can_moderate_society(user, society):
        """
        Check if user can moderate society (delete posts, manage members)
        Only admins and moderators can moderate
        """
        return SocietyMembership.objects.filter(
            user=user,
            society=society,
            status='accepted',
            role__in=['admin', 'moderator']
        ).exists()
    
    @staticmethod
    def can_manage_society(user, society):
        """
        Check if user can manage society settings
        Only admins can manage
        """
        return SocietyMembership.objects.filter(
            user=user,
            society=society,
            status='accepted',
            role='admin'
        ).exists()
    
    @staticmethod
    def is_society_creator(user, society):
        """
        Check if user is the creator of the society
        """
        return society.creator == user


class PostPermissions:
    """
    Helper class to check post-related permissions
    """
    
    @staticmethod
    def can_view_post(user, post):
        """
        Check if user can view a post based on privacy settings
        """
        # Check if poster has blocked the user
        if UserBlock.objects.filter(blocker=post.user, blocked=user).exists():
            return False
        
        # If it's a society post
        if post.society:
            return SocietyPermissions.can_view_society(user, post.society)
        
        # Personal post - check privacy
        if post.privacy == 'public':
            return True
        
        if post.privacy == 'private':
            return post.user == user
        
        if post.privacy == 'friends':
            if post.user == user:
                return True
            # Check friendship
            return Friendship.objects.filter(
                Q(requester=user, receiver=post.user, status='accepted') |
                Q(requester=post.user, receiver=user, status='accepted')
            ).exists()
        
        return False
    
    @staticmethod
    def can_edit_post(user, post):
        """
        Check if user can edit a post
        Only the post owner can edit
        """
        return post.user == user
    
    @staticmethod
    def can_delete_post(user, post):
        """
        Check if user can delete a post
        - Post owner can delete their own post
        - Society admins/moderators can delete posts in their society
        """
        if post.user == user:
            return True
        
        if post.society:
            return SocietyPermissions.can_moderate_society(user, post.society)
        
        return False
    
    @staticmethod
    def can_interact_with_post(user, post):
        """
        Check if user can like or comment on a post
        Must be able to view the post and not be blocked
        """
        # Check if user is blocked by post owner
        if UserBlock.objects.filter(blocker=post.user, blocked=user).exists():
            return False
        
        # Check if post owner is blocked by user
        if UserBlock.objects.filter(blocker=user, blocked=post.user).exists():
            return False
        
        return PostPermissions.can_view_post(user, post)


class StoryPermissions:
    """
    Helper class to check story-related permissions
    """
    
    @staticmethod
    def can_view_story(user, story):
        """
        Check if user can view a story
        """
        # Check if story is still active
        if not story.is_active():
            return False
        
        # Check if user is blocked
        if UserBlock.objects.filter(blocker=story.user, blocked=user).exists():
            return False
        
        # Check privacy
        if story.privacy == 'public':
            return True
        
        if story.privacy == 'private':
            return story.user == user
        
        if story.privacy == 'friends':
            if story.user == user:
                return True
            # Check friendship
            return Friendship.objects.filter(
                Q(requester=user, receiver=story.user, status='accepted') |
                Q(requester=story.user, receiver=user, status='accepted')
            ).exists()
        
        return False


def get_visible_posts_queryset(user):
    """
    Get queryset of posts visible to a user
    Includes both personal posts and society posts
    """
    from .models import Post, User
    
    # Get friends
    friends = User.objects.filter(
        Q(friend_requests_sent__receiver=user, friend_requests_sent__status='accepted') |
        Q(friend_requests_received__requester=user, friend_requests_received__status='accepted')
    ).distinct()
    
    # Get blocked users
    blocked_users = User.objects.filter(blocked_by__blocker=user)
    users_who_blocked = User.objects.filter(blocking__blocked=user)
    
    # Get societies user is a member of
    user_societies = SocietyMembership.objects.filter(
        user=user,
        status='accepted'
    ).values_list('society_id', flat=True)
    
    # Build the query
    posts = Post.objects.filter(
        # Personal posts
        Q(
            society__isnull=True,
            privacy='public'
        ) |
        Q(
            society__isnull=True,
            user=user
        ) |
        Q(
            society__isnull=True,
            user__in=friends,
            privacy__in=['public', 'friends']
        ) |
        # Society posts from user's societies
        Q(
            society_id__in=user_societies
        ) |
        # Public society posts
        Q(
            society__privacy='public',
            society__isnull=False
        )
    ).exclude(
        user__in=blocked_users
    ).exclude(
        user__in=users_who_blocked
    ).distinct()
    
    return posts


def get_society_posts_queryset(user, society):
    """
    Get posts from a specific society that user can view
    """
    from .models import Post, User
    
    # Check if user can view the society
    if not SocietyPermissions.can_view_society(user, society):
        return Post.objects.none()
    
    # Get blocked users
    blocked_users = User.objects.filter(blocked_by__blocker=user)
    users_who_blocked = User.objects.filter(blocking__blocked=user)
    
    # Get society posts
    posts = Post.objects.filter(
        society=society
    ).exclude(
        user__in=blocked_users
    ).exclude(
        user__in=users_who_blocked
    )
    
    return posts


def get_user_profile_posts_queryset(viewer, profile_user):
    """
    Get posts from a user's profile (excluding society posts)
    """
    from .models import Post, User
    
    # Check if viewer is blocked
    if UserBlock.objects.filter(blocker=profile_user, blocked=viewer).exists():
        return Post.objects.none()
    
    # Check if profile user is blocked by viewer
    if UserBlock.objects.filter(blocker=viewer, blocked=profile_user).exists():
        return Post.objects.none()
    
    # Check friendship
    are_friends = Friendship.objects.filter(
        Q(requester=viewer, receiver=profile_user, status='accepted') |
        Q(requester=profile_user, receiver=viewer, status='accepted')
    ).exists()
    
    # Build query based on relationship
    if viewer == profile_user:
        # Own profile - see everything
        posts = Post.objects.filter(
            user=profile_user,
            society__isnull=True  # Exclude society posts
        )
    elif are_friends:
        # Friend's profile - see public and friends posts
        posts = Post.objects.filter(
            user=profile_user,
            society__isnull=True,
            privacy__in=['public', 'friends']
        )
    else:
        # Stranger's profile - see only public posts
        posts = Post.objects.filter(
            user=profile_user,
            society__isnull=True,
            privacy='public'
        )
    
    return posts
