from apps.blocks.block_types.table.table_block import TableBlock
from apps.common.models import PurchaseOrderLine, ReceiptLine
from apps.common.filters.schemas import (
    supplier_filter,
    item_filter, item_group_filter,
    purchase_order_category_filter,
    date_from_filter,
    date_to_filter,
)
from apps.common.filters.items import item_choices_for_open_po
from apps.common.filters.business_partners import supplier_choices_for_open_po
from apps.common.filters.po_categories import po_category_choices_for_open_po
from apps.common.filters.item_groups import item_group_choices_for_open_po
class OpenPurchaseOrderLinesTable(TableBlock):
    def __init__(self):
        super().__init__("open_purchase_order_lines_table")

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        return PurchaseOrderLine.objects.filter(status="open")

    def get_filter_schema(self, request):
        return {
            "item": item_filter(self.block_name, "item__code", choices_func=item_choices_for_open_po),
            "item_group": item_group_filter(self.block_name, "item__item_group__code", choices_func=item_group_choices_for_open_po),
            "supplier": supplier_filter(self.block_name, "order__supplier__code", choices_func=supplier_choices_for_open_po),
            "category": purchase_order_category_filter(self.block_name, "order__category__code", choices_func=po_category_choices_for_open_po),

        }

class PurchaseOrderLinesTable(TableBlock):
    def __init__(self):
        super().__init__("purchase_order_lines_table")

    def get_model(self):
        return PurchaseOrderLine

    def get_filter_schema(self, request):
        return {
            "item": item_filter(self.block_name, "item__code"),
        }

class ReceiptLinesTable(TableBlock):
    def __init__(self):
        super().__init__("receipt_lines_table")

    def get_model(self):
        return ReceiptLine

    def get_filter_schema(self, request):
        return {
            # Use supplier CODE for consistency with other filters
            "supplier": supplier_filter(self.block_name, "po_line__order__supplier__code"),
            "receipt_date_from": date_from_filter("receipt_date_from", "Receipt From", "receipt_date"),
            "receipt_date_to": date_to_filter("receipt_date_to", "Receipt To", "receipt_date"),
        }
