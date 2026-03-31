"""
Development settings — overrides base with SQLite and debug mode.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Use SQLite for local development — no external DB required
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Show emails in console during development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable throttling in dev to make testing easier (optional)
# REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
