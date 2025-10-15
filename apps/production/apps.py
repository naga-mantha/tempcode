from django.apps import AppConfig


class ProductionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.production'
    verbose_name = 'Production'

    def ready(self):
        # Legacy v1 block registry disabled (migrated to specs)
        return
