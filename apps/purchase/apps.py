from django.apps import AppConfig


class PurchaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.purchase'

    def ready(self):
        # Register purchase-related blocks when the app is ready
        from apps.django_bi.blocks.registry import block_registry
        from apps.purchase.blocks_registry import register as register_blocks

        register_blocks(block_registry)
