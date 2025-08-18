from django.apps import AppConfig


class ProductionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.production'
    verbose_name = 'Production'

    def ready(self):
        # Explicitly register blocks when the app is ready
        from apps.blocks.registry import block_registry
        from apps.production.blocks_registry import register as register_blocks

        register_blocks(block_registry)
