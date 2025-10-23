"""Common utilities app configuration entry point."""

from .apps import CommonConfig

__all__ = ["CommonConfig"]

# Django < 3.2 compatibility
default_app_config = "apps.common.apps.CommonConfig"
