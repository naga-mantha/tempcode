from django.apps import AppConfig


class LayoutConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.layout"

    def ready(self):
        # Signals for auto-creating 'None' layout filters removed.
        pass
