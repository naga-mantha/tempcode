from django.apps import AppConfig


class PlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.planning'
    verbose_name = 'Planning'

    def ready(self):
        # Explicitly register blocks when the app is ready
        from django_bi.blocks.registry import block_registry
        from apps.planning.blocks_registry import register as register_blocks

        register_blocks(block_registry)

