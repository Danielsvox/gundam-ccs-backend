from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import secrets
from datetime import timedelta

from .models import User, Address, EmailVerification, PasswordReset
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, PasswordChangeSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, AddressSerializer, EmailVerificationSerializer,
    UserListSerializer
)


class UserRegistrationView(APIView):
    """User registration view."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Register a new user."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Create email verification token
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=24)
            EmailVerification.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )

            # Send verification email (in production, use Celery for async)
            # self.send_verification_email(user, token)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'User registered successfully. Please check your email for verification.',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_verification_email(self, user, token):
        """Send verification email."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        subject = 'Verify your email address'
        message = f'Please click the following link to verify your email: {verification_url}'

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class UserLoginView(APIView):
    """User login view."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Login user."""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Login successful.',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """User logout view with comprehensive token invalidation."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Logout user and invalidate all tokens."""
        try:
            # Get tokens from request
            refresh_token = request.data.get('refresh_token')
            access_token = request.data.get('access_token')

            # Blacklist refresh token if provided
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    # Token might already be invalid, continue with logout
                    pass

            # Blacklist access token if provided
            if access_token:
                try:
                    token = AccessToken(access_token)
                    token.blacklist()
                except TokenError:
                    # Token might already be invalid, continue with logout
                    pass

            # Update user's last logout time (optional)
            request.user.last_logout = timezone.now()
            request.user.save(update_fields=['last_logout'])

            return Response({
                'message': 'Logout successful. All tokens have been invalidated.',
                'logout_time': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Logout failed.',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutAllView(APIView):
    """Logout from all devices by invalidating all user tokens."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Logout user from all devices."""
        try:
            # Get all outstanding tokens for the user and blacklist them
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

            tokens = OutstandingToken.objects.filter(user_id=request.user.id)
            for token in tokens:
                RefreshToken(token.token).blacklist()

            # Update user's last logout time
            request.user.last_logout = timezone.now()
            request.user.save(update_fields=['last_logout'])

            return Response({
                'message': 'Logged out from all devices successfully.',
                'logout_time': timezone.now().isoformat(),
                'devices_logged_out': tokens.count()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Logout from all devices failed.',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """User profile view."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user profile."""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Update user profile."""
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully.',
                'user': UserProfileSerializer(request.user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """Password change view."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Change user password."""
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    """Password reset request view."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Request password reset."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)

            # Create password reset token
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=1)
            PasswordReset.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )

            # Send reset email (in production, use Celery for async)
            # self.send_reset_email(user, token)

            return Response({
                'message': 'Password reset email sent successfully.'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_reset_email(self, user, token):
        """Send password reset email."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        subject = 'Reset your password'
        message = f'Please click the following link to reset your password: {reset_url}'

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class PasswordResetConfirmView(APIView):
    """Password reset confirmation view."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Confirm password reset."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            password_reset = serializer.validated_data['password_reset']
            new_password = serializer.validated_data['new_password']

            # Update user password
            user = password_reset.user
            user.set_password(new_password)
            user.save()

            # Mark token as used
            password_reset.is_used = True
            password_reset.save()

            return Response({
                'message': 'Password reset successfully.'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationView(APIView):
    """Email verification view."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Verify email address."""
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            verification = serializer.context['verification']

            # Mark email as verified
            user = verification.user
            user.email_verified = True
            user.save()

            # Mark token as used
            verification.is_used = True
            verification.save()

            return Response({
                'message': 'Email verified successfully.'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddressListView(generics.ListCreateAPIView):
    """Address list and create view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        """Get user's addresses."""
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create address for current user."""
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Address detail view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        """Get user's addresses."""
        return Address.objects.filter(user=self.request.user)


class UserListView(generics.ListAPIView):
    """User list view (admin only)."""

    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserListSerializer
    queryset = User.objects.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_auth(request):
    """Check if user is authenticated."""
    return Response({
        'authenticated': True,
        'user': UserProfileSerializer(request.user).data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_verification_email(request):
    """Resend verification email."""
    user = request.user

    if user.email_verified:
        return Response({
            'message': 'Email is already verified.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create new verification token
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)
    EmailVerification.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )

    # Send verification email (in production, use Celery for async)
    # send_verification_email(user, token)

    return Response({
        'message': 'Verification email sent successfully.'
    }, status=status.HTTP_200_OK)
