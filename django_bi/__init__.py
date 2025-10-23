"""Django BI reusable application."""

from .conf import settings

__all__ = ["settings"]

# Django < 3.2 compatibility
default_app_config = "django_bi.apps.DjangoBiConfig"
