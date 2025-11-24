from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from urllib.parse import parse_qs

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key):
    """
    Get user from JWT token
    """
    try:
        # Decode the token
        access_token = AccessToken(token_key)
        user_id = access_token.get('user_id')
        
        # Get user
        user = User.objects.get(id=user_id)
        return user
    except (TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT
    Supports tokens from:
    1. Query string parameter 'token'
    2. Authorization header
    3. Cookies (access_token)
    """
    
    async def __call__(self, scope, receive, send):
        token = None
        
        # 1. Try to get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        # 2. If no token in query string, try to get from headers
        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        # 3. If still no token, try to get from cookies
        if not token:
            headers = dict(scope.get('headers', []))
            cookies = headers.get(b'cookie', b'').decode()
            # Parse cookies
            cookie_dict = {}
            for cookie in cookies.split(';'):
                if '=' in cookie:
                    key, value = cookie.strip().split('=', 1)
                    cookie_dict[key] = value
            token = cookie_dict.get('access_token')
        
        # Authenticate user
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Helper function to create middleware stack
    """
    return JWTAuthMiddleware(inner)
