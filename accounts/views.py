from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTP, ExtraEmail, ExtraPhoneNumber
from .serializers import ChangePasswordSerializer, ChangeEmailSerializer, ChangePhoneNumberSerializer, AddEmailSerializer, AddPhoneNumberSerializer, RegisterSerializer, LoginSerializer, UserSerializer
import random
from .utils import send_otp_email

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
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

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
            
            code = serializer.validated_data.get("code", None)
            if code and OTP.objects.filter(user=self.object, code=code).exists():
                otp_instance = OTP.objects.get(user=self.object, code=code)
                if otp_instance.is_expired():
                    return Response({"code": ["The code has expired."]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"code": ["Invalid code."]}, status=status.HTTP_400_BAD_REQUEST)
            
            otp_instance.delete()  # Invalidate OTP after use
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
    
