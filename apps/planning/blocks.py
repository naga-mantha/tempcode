from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import PlannedOrder, MrpMessage
from apps.common.filters.schemas import item_multiselect_filter, date_from_filter, date_to_filter

class PlannedPurchaseOrderTableBlock(TableBlock):
    def __init__(self):
        super().__init__("planned_purchase_order_table")  # must match what's in admin

    def get_model(self):
        return PlannedOrder

    def get_base_queryset(self, user):
        # Apply base filter for planned purchase orders only
        return PlannedOrder.objects.filter(type="PPUR")

    # Inherit default get_column_defs from TableBlock

    def get_filter_schema(self, request):
        from apps.common.filters.schemas import item_multiselect_filter

        return {
            "item": item_multiselect_filter(self.block_name, "item__code"),
            "planned_start_date_from": date_from_filter("planned_start_date_from", "Planned Start From", "planned_start_date"),
            "planned_start_date_to": date_to_filter("planned_start_date_to", "Planned Start To", "planned_start_date"),
        }

class PlannedOrderPivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("planned_order_pivot")

    def get_model(self):
        return PlannedOrder

    def get_base_queryset(self, user):
        # Default pivot scope: planned purchase orders only (PPUR)
        return PlannedOrder.objects.filter(type="PPUR")

    def get_filter_schema(self, request):
        # Allow filtering by PlannedOrder.type (e.g., PPUR/PPRO) and optionally Item
        def type_choices(user):
            return [("PPUR", "Purchase"), ("PPRO", "Production")]

        return {
            "type": {
                "label": "Type",
                "type": "select",
                "choices": type_choices,
                "handler": lambda qs, val: qs.filter(type=val) if val else qs,
            },
            "item": item_multiselect_filter(self.block_name, "item__code"),
            "planned_start_date_from": date_from_filter("planned_start_date_from", "Planned Start From", "planned_start_date"),
            "planned_start_date_to": date_to_filter("planned_start_date_to", "Planned Start To", "planned_start_date"),
        }

class MRPMessageTableBlock(TableBlock):
    def __init__(self):
        super().__init__("mrp_message_table")  # must match what's in admin

    def get_model(self):
        return MrpMessage

    def get_filter_schema(self, request):
        from apps.common.filters.schemas import item_multiselect_filter_any

        return {
            # Filter by Item across either Purchase or Production linked objects
            "item": item_multiselect_filter_any(
                self.block_name,
                ["pol__item__code", "production_order__item__code"],
            ),
        }
