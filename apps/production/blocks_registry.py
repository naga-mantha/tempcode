from apps.production.blocks import (
    ProductionOrderTableBlock,
    ProductionOrderOperationTableBlock,
)


def register(registry):
    """Register production related blocks."""

    registry.register("production_order_table", ProductionOrderTableBlock())
    registry.register("production_order_operation_table", ProductionOrderOperationTableBlock())

