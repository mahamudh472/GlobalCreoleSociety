from django.urls import path
from accounts.views import (
    AddEmailView, AddPhoneNumberView, ChangeEmailView, ChangePasswordView, 
    ChangePhoneNumberView, RegisterView, LoginView, LogoutView, SendOTPView, 
    UserLockView, UserProfileView, OtherUserProfileView, CookieTokenRefreshView
)


urlpatterns = [  
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/<uuid:id>/', OtherUserProfileView.as_view(), name='other_user_profile'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('change-email/', ChangeEmailView.as_view(), name='change_email'),
    path('change-phone-number/', ChangePhoneNumberView.as_view(), name='change_phone_number'),
    path('add-email/', AddEmailView.as_view(), name='add_email'),
    path('add-phone-number/', AddPhoneNumberView.as_view(), name='add_phone_number'),
    path('profile-lock/', UserLockView.as_view(), name='profile_lock'),
]