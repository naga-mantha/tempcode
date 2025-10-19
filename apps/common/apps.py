from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'

    def ready(self):
        super().ready()
        try:
            from apps.blocks.registry import get_registry, register
        except ImportError:
            return

        from .tables.items_table import ItemsTableSpec
        from .pivots.items_pivot import ItemsPivotSpec

        registry = get_registry()
        for spec in (ItemsTableSpec.spec, ItemsPivotSpec.spec):
            if spec.id not in registry:
                register(spec)