from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('logout-all/', views.UserLogoutAllView.as_view(), name='logout_all'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('change-password/', views.PasswordChangeView.as_view(),
         name='change_password'),

    # Password Reset
    path('password-reset/', views.PasswordResetRequestView.as_view(),
         name='password_reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),

    # Email Verification
    path('email-verify/', views.EmailVerificationView.as_view(), name='email_verify'),

    # Address Management
    path('addresses/', views.AddressListView.as_view(), name='address_list'),
    path('addresses/<int:pk>/', views.AddressDetailView.as_view(),
         name='address_detail'),

    # User List (for admin purposes)
    path('users/', views.UserListView.as_view(), name='user_list'),
]
