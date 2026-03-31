"""
Custom exception handler and shared utilities.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Wraps default DRF exceptions in a consistent JSON envelope:
    {
        "success": false,
        "errors": { ... }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'success': False,
            'errors': response.data,
        }

    return response


def get_client_ip(request) -> str:
    """Extract the real client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def get_tokens_for_user(user):
    """
    Generate JWT access + refresh token pair for a user.
    Returns a dict with 'access' and 'refresh' keys.
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
