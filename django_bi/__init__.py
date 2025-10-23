"""Django BI reusable application."""

from .apps import DjangoBiConfig
from .conf import settings

__all__ = ["settings", "DjangoBiConfig"]

# Django < 3.2 compatibility
default_app_config = "django_bi.apps.DjangoBiConfig"
