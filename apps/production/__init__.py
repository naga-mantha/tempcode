"""Production app configuration entry point."""

from .apps import ProductionConfig

__all__ = ["ProductionConfig"]

# Django < 3.2 compatibility
default_app_config = "apps.production.apps.ProductionConfig"
