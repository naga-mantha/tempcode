from apps.purchase.blocks import (
    PurchaseGenericPivot,
    PurchaseOverdueByBuyerPivot,
    PurchaseBuyerOverdueRepeaterBlock,
)


def register(registry):
    """Register purchase related blocks."""

    registry.register("purchase_generic_pivot", PurchaseGenericPivot())
    registry.register("purchase_overdue_by_buyer", PurchaseOverdueByBuyerPivot())
    registry.register("purchase_buyer_overdue_repeater", PurchaseBuyerOverdueRepeaterBlock())
