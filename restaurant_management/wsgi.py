"""
WSGI config for restaurant_management project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_management.settings.development')
application = get_wsgi_application()
