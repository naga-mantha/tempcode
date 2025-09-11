from apps.planning.blocks import (
    PlannedPurchaseOrderTableBlock,
    PlannedOrderPivot,
    MRPMessageTableBlock
)


def register(registry):
    """Register purchase related blocks."""

    registry.register("planned_purchase_order_table", PlannedPurchaseOrderTableBlock())
    registry.register("planned_order_pivot", PlannedOrderPivot())
    registry.register("mrp_message_table", MRPMessageTableBlock())
