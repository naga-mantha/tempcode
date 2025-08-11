from apps.production.blocks import ProductionOrderTableBlock
from apps.blocks.registry import block_registry


def register(registry=block_registry):
    """Register production related blocks."""

    registry.register("production_order_table", ProductionOrderTableBlock())


# Register immediately on import for backward compatibility.
register()

