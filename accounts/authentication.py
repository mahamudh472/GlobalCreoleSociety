"""
Custom authentication classes for handling both cookie and header-based JWT authentication.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that checks both Authorization header and cookies.
    
    Priority:
    1. First checks Authorization header (for mobile apps)
    2. If not found, checks cookies (for web browsers)
    """
    
    def authenticate(self, request):
        # First, try to get token from header (standard JWT authentication)
        header = self.get_header(request)
        
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
        
        # If no token in header, try to get from cookie
        raw_token = request.COOKIES.get('access_token')
        
        if raw_token is None:
            return None
        
        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            raise AuthenticationFailed('Invalid token in cookie')
        
        return self.get_user(validated_token), validated_token
