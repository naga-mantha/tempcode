from django.apps import AppConfig

class LayoutConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.layout'

    def ready(self):
        import apps.layout.signals
