from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings
from .models import User, OTP, ExtraEmail, ExtraPhoneNumber
from .serializers import ChangePasswordSerializer, ChangeEmailSerializer, ChangePhoneNumberSerializer, AddEmailSerializer, AddPhoneNumberSerializer, RegisterSerializer, LoginSerializer, UserSerializer
import random
from .utils import send_otp_email


def set_token_cookies(response, access_token, refresh_token):
    """
    Helper function to set JWT tokens in cookies
    """
    # Get cookie settings from Django settings or use defaults
    cookie_samesite = getattr(settings, 'JWT_COOKIE_SAMESITE', 'Lax')
    cookie_secure = getattr(settings, 'JWT_COOKIE_SECURE', False)
    cookie_httponly = getattr(settings, 'JWT_COOKIE_HTTPONLY', True)
    cookie_domain = getattr(settings, 'JWT_COOKIE_DOMAIN', None)
    cookie_path = getattr(settings, 'JWT_COOKIE_PATH', '/')
    
    # Get token lifetimes from Simple JWT settings
    access_token_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME')
    refresh_token_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')
    
    # Set access token cookie
    response.set_cookie(
        key='access_token',
        value=access_token,
        max_age=int(access_token_lifetime.total_seconds()) if access_token_lifetime else 3600,  # 1 hour default
        httponly=cookie_httponly,
        secure=cookie_secure,
        samesite=cookie_samesite,
        domain=cookie_domain,
        path=cookie_path,
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        max_age=int(refresh_token_lifetime.total_seconds()) if refresh_token_lifetime else 604800,  # 7 days default
        httponly=cookie_httponly,
        secure=cookie_secure,
        samesite=cookie_samesite,
        domain=cookie_domain,
        path=cookie_path,
    )
    
    return response


def delete_token_cookies(response):
    """
    Helper function to delete JWT tokens from cookies
    """
    cookie_domain = getattr(settings, 'JWT_COOKIE_DOMAIN', None)
    cookie_path = getattr(settings, 'JWT_COOKIE_PATH', '/')
    
    response.delete_cookie(
        key='access_token',
        domain=cookie_domain,
        path=cookie_path,
    )
    
    response.delete_cookie(
        key='refresh_token',
        domain=cookie_domain,
        path=cookie_path,
    )
    
    return response

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens for the new user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response_data = {
            'user': UserSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': refresh_token,
                'access': access_token,
            },
            'message': 'User registered successfully'
        }
        
        response = Response(response_data, status=status.HTTP_201_CREATED)
        
        # Set tokens in cookies for web browsers
        response = set_token_cookies(response, access_token, refresh_token)
        
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response_data = {
            'user': UserSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': refresh_token,
                'access': access_token,
            },
            'message': 'Login successful'
        }
        
        response = Response(response_data, status=status.HTTP_200_OK)
        
        # Set tokens in cookies for web browsers
        response = set_token_cookies(response, access_token, refresh_token)
        
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Try to get refresh token from request body first (for mobile apps)
            refresh_token = request.data.get('refresh')
            
            # If not in body, try to get from cookies (for web browsers)
            if not refresh_token:
                refresh_token = request.COOKIES.get('refresh_token')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            response = Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
            
            # Clear cookies for web browsers
            response = delete_token_cookies(response)
            
            return response
        except Exception as e:
            response = Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            # Still try to clear cookies even if blacklist fails
            response = delete_token_cookies(response)
            return response


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class OtherUserProfileView(generics.RetrieveAPIView):
    """View any user's profile by user ID"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Check if profile is locked
        # if user.profile_lock and user != request.user:
        #     return Response(
        #         {"detail": "This profile is private."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        serializer = self.get_serializer(user, context={'request': request})
        return Response(serializer.data)


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.validated_data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            self.object.set_password(serializer.validated_data.get("new_password"))
            self.object.save()
            return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeEmailView(generics.UpdateAPIView):
    serializer_class = ChangeEmailSerializer
    model = User
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check password
            if not self.object.check_password(serializer.validated_data.get("password")):
                return Response({"password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check OTP
            code = serializer.validated_data.get("code", None)
            if code and OTP.objects.filter(user=self.object, code=code).exists():
                otp_instance = OTP.objects.get(user=self.object, code=code)
                if otp_instance.is_expired():
                    return Response({"code": ["The code has expired."]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"code": ["Invalid code."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if email is already in use
            new_email = serializer.validated_data.get("new_email")
            if User.objects.filter(email=new_email).exists():
                return Response({"new_email": ["This email is already in use."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update email and invalidate OTP
            otp_instance.delete()
            self.object.email = new_email
            self.object.save()
            return Response({"message": "Email updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePhoneNumberView(generics.UpdateAPIView):
    serializer_class = ChangePhoneNumberSerializer
    model = User
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check password
            if not self.object.check_password(serializer.validated_data.get("password")):
                return Response({"password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check OTP
            code = serializer.validated_data.get("code", None)
            if code and OTP.objects.filter(user=self.object, code=code).exists():
                otp_instance = OTP.objects.get(user=self.object, code=code)
                if otp_instance.is_expired():
                    return Response({"code": ["The code has expired."]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"code": ["Invalid code."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if phone number is already in use
            new_phone_number = serializer.validated_data.get("new_phone_number")
            if User.objects.filter(phone_number=new_phone_number).exists():
                return Response({"new_phone_number": ["This phone number is already in use."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update phone number and invalidate OTP
            otp_instance.delete()
            self.object.phone_number = new_phone_number
            self.object.save()
            return Response({"message": "Phone number updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddEmailView(generics.CreateAPIView):
    serializer_class = AddEmailSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check password
            if not user.check_password(serializer.validated_data.get("password")):
                return Response({"password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check OTP
            code = serializer.validated_data.get("code", None)
            if code and OTP.objects.filter(user=user, code=code).exists():
                otp_instance = OTP.objects.get(user=user, code=code)
                if otp_instance.is_expired():
                    return Response({"code": ["The code has expired."]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"code": ["Invalid code."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if email is already in use (in User model or ExtraEmail model)
            email = serializer.validated_data.get("email")
            if User.objects.filter(email=email).exists() or ExtraEmail.objects.filter(email=email).exists():
                return Response({"email": ["This email is already in use."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create extra email and invalidate OTP
            otp_instance.delete()
            extra_email = ExtraEmail.objects.create(user=user, email=email, is_verified=True)
            return Response({
                "message": "Email added successfully",
                "email": extra_email.email,
                "id": extra_email.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddPhoneNumberView(generics.CreateAPIView):
    serializer_class = AddPhoneNumberSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check password
            if not user.check_password(serializer.validated_data.get("password")):
                return Response({"password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check OTP
            code = serializer.validated_data.get("code", None)
            if code and OTP.objects.filter(user=user, code=code).exists():
                otp_instance = OTP.objects.get(user=user, code=code)
                if otp_instance.is_expired():
                    return Response({"code": ["The code has expired."]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"code": ["Invalid code."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if phone number is already in use (in User model or ExtraPhoneNumber model)
            phone_number = serializer.validated_data.get("phone_number")
            if User.objects.filter(phone_number=phone_number).exists() or ExtraPhoneNumber.objects.filter(phone_number=phone_number).exists():
                return Response({"phone_number": ["This phone number is already in use."]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create extra phone number and invalidate OTP
            otp_instance.delete()
            extra_phone = ExtraPhoneNumber.objects.create(user=user, phone_number=phone_number, is_verified=True)
            return Response({
                "message": "Phone number added successfully",
                "phone_number": extra_phone.phone_number,
                "id": extra_phone.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteExtraEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, email_id):
        user = request.user
        try:
            extra_email = ExtraEmail.objects.get(id=email_id, user=user)
            extra_email.delete()
            return Response({'message': 'Email removed successfully'}, status=status.HTTP_200_OK)
        except ExtraEmail.DoesNotExist:
            return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)


class DeleteExtraPhoneNumberView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, phone_id):
        user = request.user
        try:
            extra_phone = ExtraPhoneNumber.objects.get(id=phone_id, user=user)
            extra_phone.delete()
            return Response({'message': 'Phone number removed successfully'}, status=status.HTTP_200_OK)
        except ExtraPhoneNumber.DoesNotExist:
            return Response({'error': 'Phone number not found'}, status=status.HTTP_404_NOT_FOUND)


class SendOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = random.randint(100000, 999999)
        otp_instance = OTP.create_otp(OTP, user=user, code=code)

        send_otp_email(user.email, code)
        
        print(f"OTP for user {user.email}: {code}")  # For demonstration purposes only
        
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)


class UserLockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.profile_lock = not user.profile_lock
        user.save()
        status_msg = 'locked' if user.profile_lock else 'unlocked'
        return Response({'message': f'Profile has been {status_msg}.'}, status=status.HTTP_200_OK)


class CookieTokenRefreshView(BaseTokenRefreshView):
    """
    Custom token refresh view that handles both cookie and body-based refresh tokens.
    
    For mobile apps: Send refresh token in request body
    For web browsers: Refresh token is automatically read from cookies
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Try to get refresh token from request body first (for mobile apps)
        refresh_token = request.data.get('refresh')
        
        # If not in body, try to get from cookies (for web browsers)
        if not refresh_token:
            refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found in request body or cookies'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a mutable copy of request.data if needed
        if not request.data.get('refresh'):
            request._full_data = {'refresh': refresh_token}
        
        try:
            # Call parent class method to refresh the token
            response = super().post(request, *args, **kwargs)
            
            # If successful, set the new tokens in cookies
            if response.status_code == 200:
                access_token = response.data.get('access')
                refresh_token = response.data.get('refresh')
                
                if access_token:
                    # Set new tokens in cookies for web browsers
                    response = set_token_cookies(response, access_token, refresh_token or request.COOKIES.get('refresh_token'))
            
            return response
        except InvalidToken as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserSearchView(generics.ListAPIView):
    """
    Search for users by name, email, or username.
    Returns users matching the search query.
    
    Query Parameters:
    - q: Search query string (required)
    - limit: Maximum number of results (default: 10, max: 50)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        from django.db.models import Q
        
        query = self.request.query_params.get('q', '').strip()
        limit = min(int(self.request.query_params.get('limit', 10)), 50)
        
        if not query:
            return User.objects.none()
        
        # Search by profile_name or email
        # Exclude the current user from results
        return User.objects.filter(
            Q(profile_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(
            id=self.request.user.id
        ).order_by('profile_name')[:limit]
    
    def list(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({
                'results': [],
                'count': 0,
                'message': 'Please provide a search query'
            })
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'results': serializer.data,
            'count': len(serializer.data),
            'query': query
        })
    
