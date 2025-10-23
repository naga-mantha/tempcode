"""Planning app configuration entry point."""

from .apps import PlanningConfig

__all__ = ["PlanningConfig"]

# Django < 3.2 compatibility
default_app_config = "apps.planning.apps.PlanningConfig"
