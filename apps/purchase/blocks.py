from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import PurchaseOrderLine
from apps.common.models.receipts import ReceiptLine
from apps.common.filters.schemas import (
    supplier_filter,
    item_multiselect_filter,
    date_from_filter,
    date_to_filter,
)

class ReceiptLinesTableBlock(TableBlock):
    def __init__(self):
        super().__init__("receipt_lines_table")

    def get_model(self):
        return ReceiptLine

    def get_filter_schema(self, request):
        return {
            "supplier": supplier_filter(self.block_name, "po_line__order__supplier_id"),
            "receipt_date_from": date_from_filter("receipt_date_from", "Receipt From", "receipt_date"),
            "receipt_date_to": date_to_filter("receipt_date_to", "Receipt To", "receipt_date"),
        }

class PurchaseOrderLineTableBlock(TableBlock):
    def __init__(self):
        super().__init__("purchase_order_lines_table")  # must match what's in admin

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        return PurchaseOrderLine.objects.filter(status="open").exclude(back_order=0)

    def get_filter_schema(self, request):
        return {
            "item": item_multiselect_filter(self.block_name, "item__code"),
        }

class PurchaseOrderLinePivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("purchase_order_line_pivot")

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        # Limit pivot to open purchase order lines by default
        return PurchaseOrderLine.objects.filter(status="open").exclude(back_order=0)

