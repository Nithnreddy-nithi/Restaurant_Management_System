"""
Custom throttle classes for the users app.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Throttles login attempts to 5 per minute per IP.
    Scope must match a key in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
    """
    scope = 'login'


class LoginUserRateThrottle(UserRateThrottle):
    """
    For authenticated users hitting login-like endpoints.
    """
    scope = 'login'
