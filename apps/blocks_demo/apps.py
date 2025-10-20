"""Configuration for the Blocks Demo Django application."""

from django.apps import AppConfig


class BlocksDemoConfig(AppConfig):
    """Application configuration for the blocks demo."""

    name = "apps.blocks_demo"
    verbose_name = "Blocks Demo"

    def ready(self) -> None:
        """Run initialization routines for the app.

        The initialization handles loading demo data and registering blocks so
        they become available to the rest of the project. The helper module is
        isolated to keep the ready hook tidy and easily testable.
        """

        from . import initialization

        initialization.load_initial_data()
        initialization.register_blocks()
