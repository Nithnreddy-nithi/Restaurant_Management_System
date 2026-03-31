"""
Signal handlers for the users app.
Captures auth events and writes them to the AuditLog.
"""
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out

from apps.users.models import AuditLog
from apps.users.utils import get_client_ip


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Record a login audit log entry."""
    if request is None:
        return
    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.LOGIN,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Record a logout audit log entry."""
    if request is None or user is None:
        return
    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.LOGOUT,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
