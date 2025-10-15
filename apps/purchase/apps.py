from django.apps import AppConfig


class PurchaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.purchase'

    def ready(self):
        # Legacy v1 block registry disabled (migrated to specs)
        return
