"""Purchase app configuration entry point."""

from .apps import PurchaseConfig

__all__ = ["PurchaseConfig"]

# Django < 3.2 compatibility
default_app_config = "apps.purchase.apps.PurchaseConfig"
