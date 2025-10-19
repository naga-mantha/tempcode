from django.apps import AppConfig

class BlocksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blocks"

    def ready(self):
        # Initialize v2-style specs into the registry
        try:
            from .register import load_specs
            load_specs()
        except Exception:
            # Fail-safe: do not block app startup on spec loading
            pass

