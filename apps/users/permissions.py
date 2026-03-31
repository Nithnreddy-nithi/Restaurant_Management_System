"""
Role-based permission classes for the users app.
"""
from rest_framework.permissions import BasePermission

from apps.users.models import Role


class IsAdminRole(BasePermission):
    """
    Allows access only to users with the Admin role.
    """
    message = 'Access restricted to Admin users only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Admins have full access; authenticated staff get read-only access.
    """
    message = 'Write operations restricted to Admin users.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == Role.ADMIN


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level: allows owners to access their own resource, or Admins.
    """
    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == Role.ADMIN:
            return True
        return obj == request.user


class IsStaffRole(BasePermission):
    """
    Allows access to any authenticated staff member (any role).
    """
    message = 'Access restricted to authenticated staff members.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in Role.values
        )
