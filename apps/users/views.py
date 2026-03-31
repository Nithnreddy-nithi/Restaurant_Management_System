"""
Views for the users app.
All logic stays lean — heavy lifting is done in serializers and utils.
"""
from django.contrib.auth import login as django_login
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from apps.users.models import AuditLog, CustomUser
from apps.users.permissions import IsAdminRole, IsOwnerOrAdmin
from apps.users.serializers import (
    AdminUserProfileSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from apps.users.throttles import LoginRateThrottle
from apps.users.utils import get_client_ip, get_tokens_for_user


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
class RegisterView(generics.CreateAPIView):
    """
    POST /api/users/register/
    Creates a new user account. No authentication required.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Audit log
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.REGISTER,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        tokens = get_tokens_for_user(user)
        profile = UserProfileSerializer(user, context={'request': request})

        return Response(
            {
                'success': True,
                'message': 'Account created successfully.',
                'user': profile.data,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class LoginView(APIView):
    """
    POST /api/users/login/
    Authenticates via email + password, returns JWT pair.
    Throttled to 5 requests/min per IP.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Fire Django login signal → triggers AuditLog via signal handler
        django_login(request, user)

        tokens = get_tokens_for_user(user)
        profile = UserProfileSerializer(user, context={'request': request})

        return Response(
            {
                'success': True,
                'message': 'Login successful.',
                'user': profile.data,
                **tokens,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
class LogoutView(APIView):
    """
    POST /api/users/logout/
    Blacklists the provided refresh token, effectively logging out the user.
    Requires: { "refresh": "<token>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            token.blacklist()
        except TokenError as e:
            return Response(
                {'success': False, 'errors': {'refresh': str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.LOGOUT,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return Response(
            {'success': True, 'message': 'Logged out successfully.'},
            status=status.HTTP_205_RESET_CONTENT,
        )


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------
class TokenRefreshView(BaseTokenRefreshView):
    """
    POST /api/users/token/refresh/
    Returns a new access token (and rotated refresh token if rotation is ON).
    Wraps SimpleJWT's built-in view with an audit log entry.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            AuditLog.objects.create(
                user=None,  # user is not authenticated via access token here
                action=AuditLog.Action.TOKEN_REFRESH,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            response.data = {
                'success': True,
                **response.data,
            }

        return response


# ---------------------------------------------------------------------------
# Profile — own user
# ---------------------------------------------------------------------------
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/profile/  — Returns the authenticated user's profile.
    PATCH /api/users/profile/ — Updates editable profile fields.
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.user.is_admin:
            return AdminUserProfileSerializer
        return UserProfileSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': serializer.data})


# ---------------------------------------------------------------------------
# Change Password
# ---------------------------------------------------------------------------
class ChangePasswordView(APIView):
    """
    POST /api/users/change-password/
    Allows authenticated users to update their password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])

        return Response(
            {'success': True, 'message': 'Password updated successfully.'},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Admin — list all users
# ---------------------------------------------------------------------------
class UserListView(generics.ListAPIView):
    """
    GET /api/users/
    Returns a paginated list of all users. Admin only.
    """
    serializer_class = AdminUserProfileSerializer
    permission_classes = [IsAdminRole]
    queryset = CustomUser.objects.all()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'data': serializer.data})


# ---------------------------------------------------------------------------
# Admin — manage single user
# ---------------------------------------------------------------------------
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/users/<id>/   — Retrieve a specific user (Admin only).
    PATCH  /api/users/<id>/   — Update role or status (Admin only).
    DELETE /api/users/<id>/   — Deactivate user (Admin only).
    """
    serializer_class = AdminUserProfileSerializer
    permission_classes = [IsAdminRole]
    queryset = CustomUser.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        """Soft-delete: deactivate instead of deleting."""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(
            {'success': True, 'message': 'User deactivated successfully.'},
            status=status.HTTP_200_OK,
        )
