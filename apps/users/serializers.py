"""
Serializers for the users app.
Handles registration, login, profile, password change, and token operations.
"""
import re

from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser, Role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#])[A-Za-z\d@$!%*?&_\-#]{8,}$'
)


def validate_password_strength(value: str) -> str:
    """
    Enforces: min 8 chars, uppercase, lowercase, digit, special char.
    """
    if not PASSWORD_REGEX.match(value):
        raise serializers.ValidationError(
            _(
                'Password must be at least 8 characters and contain: '
                'uppercase letter, lowercase letter, digit, and special character (@$!%*?&_-#).'
            )
        )
    return value


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'phone_number', 'role', 'password', 'password_confirm',
        ]
        extra_kwargs = {
            'role': {'default': Role.WAITER},
        }

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match.')})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password')

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user:
            raise serializers.ValidationError(
                {'non_field_errors': [_('Invalid email or password.')]}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {'non_field_errors': [_('This account has been deactivated.')]}
            )

        attrs['user'] = user
        return attrs


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class UserProfileSerializer(serializers.ModelSerializer):
    """Read + partial update of own profile. Role is read-only for non-admins."""

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone_number', 'role', 'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'email', 'role', 'date_joined', 'last_login']


class AdminUserProfileSerializer(UserProfileSerializer):
    """Extended profile serializer for admins — allows role updates."""

    class Meta(UserProfileSerializer.Meta):
        read_only_fields = ['id', 'email', 'date_joined', 'last_login']


# ---------------------------------------------------------------------------
# Token response helpers
# ---------------------------------------------------------------------------
class TokenResponseSerializer(serializers.Serializer):
    """Used only for Swagger/OpenAPI schema documentation."""
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserProfileSerializer(read_only=True)


# ---------------------------------------------------------------------------
# Change Password
# ---------------------------------------------------------------------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {'new_password_confirm': _('New passwords do not match.')}
            )
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_('Old password is incorrect.'))
        return value


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        help_text=_('The refresh token to blacklist.')
    )

    def validate_refresh(self, value):
        try:
            RefreshToken(value)
        except Exception:
            raise serializers.ValidationError(_('Invalid or expired refresh token.'))
        return value
