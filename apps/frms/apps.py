from django.apps import AppConfig


class FrmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.frms'

    def ready(self):
        # this will import signals.py and register handlers
        import apps.frms.signals

        from apps.frms.filters import get_filter_schema
        from apps.layout import filter_registry
        filter_registry.register("newemployee", get_filter_schema)

