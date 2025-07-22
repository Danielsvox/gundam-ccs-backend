from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Address, EmailVerification, PasswordReset


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name',
                  'password', 'phone')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        """Create a new user."""
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        """Validate user credentials."""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError(
                'Must include email and password.')

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'phone', 'avatar',
                  'email_verified', 'phone_verified', 'date_of_birth', 'date_joined', 'last_login')
        read_only_fields = ('id', 'email', 'email_verified',
                            'phone_verified', 'date_joined', 'last_login')


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',
                  'phone', 'avatar', 'date_of_birth')


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password])

    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate email exists."""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'No user found with this email address.')
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

    def validate(self, attrs):
        """Validate password reset."""
        # Validate token
        try:
            password_reset = PasswordReset.objects.get(
                token=attrs['token'],
                is_used=False
            )
            attrs['password_reset'] = password_reset
        except PasswordReset.DoesNotExist:
            raise serializers.ValidationError(
                'Invalid or expired reset token.')

        return attrs


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for user addresses."""

    class Meta:
        model = Address
        fields = ('id', 'address_type', 'first_name', 'last_name', 'company',
                  'address_line_1', 'address_line_2', 'city', 'state', 'postal_code',
                  'country', 'phone', 'is_default', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        """Validate address data."""
        # Ensure only one default address per user
        if attrs.get('is_default', False):
            user = self.context['request'].user
            Address.objects.filter(
                user=user, is_default=True).update(is_default=False)
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""

    token = serializers.CharField()

    def validate_token(self, value):
        """Validate verification token."""
        try:
            verification = EmailVerification.objects.get(
                token=value,
                is_used=False
            )
            self.context['verification'] = verification
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError(
                'Invalid or expired verification token.')
        return value


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users (admin only)."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_active',
                  'email_verified', 'date_joined')
        read_only_fields = ('id', 'email', 'date_joined')
