from apps.purchase.blocks import (
    ReceiptLinesTableBlock,
    PurchaseOrderLineTableBlock,
    PurchaseOrderLinePivot,
)
from apps.purchase.charts import PurchaseOtdDialChart


def register(registry):
    """Register purchase related blocks."""

    registry.register("receipt_lines_table", ReceiptLinesTableBlock())
    registry.register("purchase_otd_dial", PurchaseOtdDialChart())
    registry.register("purchase_order_lines_table", PurchaseOrderLineTableBlock())
    registry.register("purchase_order_line_pivot", PurchaseOrderLinePivot())



