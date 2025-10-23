from django_bi.blocks.block_types.table.table_block import TableBlock
from apps.common.models import PurchaseOrderLine, ReceiptLine
from apps.common.filters.schemas import (
    supplier_filter,
    item_filter,
    item_group_filter,
    item_group_type_filter,
    program_filter,
    item_type_filter,
    mrp_reschedule_direction_filter,
    purchase_order_category_filter,
    date_from_filter,
    date_to_filter,
)
from apps.common.filters.items import item_choices_for_open_po
from apps.common.filters.business_partners import supplier_choices_for_open_po
from apps.common.filters.po_categories import po_category_choices_for_open_po
from apps.common.filters.item_groups import item_group_choices_for_open_po
from apps.common.filters.item_group_types import item_group_type_choices_for_open_po
from apps.common.filters.programs import program_choices_for_open_po
from apps.common.filters.item_types import item_type_choices_for_open_po
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
            "item_group_type": item_group_type_filter(self.block_name, "item__item_group__type__code", choices_func=item_group_type_choices_for_open_po),
            "program": program_filter(self.block_name, "item__item_group__program__code", choices_func=program_choices_for_open_po),
            "item_type": item_type_filter(self.block_name, "item__type__code", choices_func=item_type_choices_for_open_po),
            "supplier": supplier_filter(self.block_name, "order__supplier__code", choices_func=supplier_choices_for_open_po),
            "category": purchase_order_category_filter(self.block_name, "order__category__code", choices_func=po_category_choices_for_open_po),
            "order_date_from": date_from_filter("order_date_from", "Order Date From", "order_date"),
            "order_date_to": date_to_filter("order_date_to", "Order Date To", "order_date"),
            "final_receive_date_from": date_from_filter("final_receive_date_from", "Final Receive From", "final_receive_date"),
            "final_receive_date_to": date_to_filter("final_receive_date_to", "Final Receive To", "final_receive_date"),
            "mrp_reschedule_date_from": date_from_filter("mrp_reschedule_date_from", "MRP Reschedule From", "mrp_message__mrp_reschedule_date"),
            "mrp_reschedule_date_to": date_to_filter("mrp_reschedule_date_to", "MRP Reschedule To", "mrp_message__mrp_reschedule_date"),
            "mrp_direction": mrp_reschedule_direction_filter(self.block_name, "mrp_message__direction"),
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
