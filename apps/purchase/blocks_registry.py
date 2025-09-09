from apps.purchase.blocks import (
    PurchaseGenericPivot,
    PurchaseOverdueByBuyerPivot,
    PurchaseBuyerOverdueRepeaterBlock,
    PurchaseOtdRepeaterBlock,
    ReceiptLinesTableBlock,
    SupplierByMonthSummaryTableBlock,
)
from apps.purchase.charts import PurchaseOtdDialChart


def register(registry):
    """Register purchase related blocks."""

    registry.register("purchase_generic_pivot", PurchaseGenericPivot())
    registry.register("purchase_overdue_by_buyer", PurchaseOverdueByBuyerPivot())
    registry.register("purchase_buyer_overdue_repeater", PurchaseBuyerOverdueRepeaterBlock())
    registry.register("receipt_lines_table", ReceiptLinesTableBlock())
    registry.register("supplier_by_month_summary_table", SupplierByMonthSummaryTableBlock())
    registry.register("purchase_otd_dial", PurchaseOtdDialChart())
    registry.register("purchase_otd_repeater", PurchaseOtdRepeaterBlock())
