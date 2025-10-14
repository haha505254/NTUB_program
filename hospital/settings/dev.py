from __future__ import annotations

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOCAL_CSRF_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

for origin in LOCAL_CSRF_ORIGINS:
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
