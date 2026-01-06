from django.urls import path
from accounts.views import (
    AddEmailView, AddPhoneNumberView, ChangeEmailView, ChangePasswordView, 
    ChangePhoneNumberView, DeleteExtraEmailView, DeleteExtraPhoneNumberView,
    RegisterView, LoginView, LogoutView, SendOTPView, 
    UserLockView, UserProfileView, OtherUserProfileView, CookieTokenRefreshView,
    UserSearchView,
    LocationListCreateView, LocationDetailView,
    WorkListCreateView, WorkDetailView,
    EducationListCreateView, EducationDetailView, ResetPasswordView
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
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('change-email/', ChangeEmailView.as_view(), name='change_email'),
    path('change-phone-number/', ChangePhoneNumberView.as_view(), name='change_phone_number'),
    path('add-email/', AddEmailView.as_view(), name='add_email'),
    path('add-phone-number/', AddPhoneNumberView.as_view(), name='add_phone_number'),
    path('delete-email/<int:email_id>/', DeleteExtraEmailView.as_view(), name='delete_extra_email'),
    path('delete-phone-number/<int:phone_id>/', DeleteExtraPhoneNumberView.as_view(), name='delete_extra_phone'),
    path('profile-lock/', UserLockView.as_view(), name='profile_lock'),
    path('search/', UserSearchView.as_view(), name='user_search'),
    # Locations
    path('locations/', LocationListCreateView.as_view(), name='location_list_create'),
    path('locations/<int:pk>/', LocationDetailView.as_view(), name='location_detail'),
    # Works
    path('works/', WorkListCreateView.as_view(), name='work_list_create'),
    path('works/<int:pk>/', WorkDetailView.as_view(), name='work_detail'),
    # Education
    path('educations/', EducationListCreateView.as_view(), name='education_list_create'),
    path('educations/<int:pk>/', EducationDetailView.as_view(), name='education_detail'),
]