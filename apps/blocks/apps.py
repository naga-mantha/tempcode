from django.apps import AppConfig


class BlocksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blocks'

    def ready(self):
        import apps.blocks.signals.field_display_rule_signals