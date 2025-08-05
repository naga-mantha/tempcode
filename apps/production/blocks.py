from apps.blocks.blocks.table.table_block import TableBlock
from apps.common.models import ProductionOrder
from apps.blocks.helpers.filter_config import apply_filter_registry

class ProductionOrderTableBlock(TableBlock):
    def __init__(self):
        super().__init__("production_order_table")  # must match what's in admin

    def get_model(self):
        return ProductionOrder

    def get_queryset(self, user, filters):
        qs = ProductionOrder.objects.all()
        return apply_filter_registry("production_order_table", qs, filters, user)

    def get_field_labels(self, user):
        return {
            "production_order": "Order #",
            "status": "Status",
            "quantity": "Quantity",
            "due_date": "Due Date",
        }

    def get_tabulator_options(self, user):
        return {
            "layout": "fitColumns",
            "pagination": "local",
            "paginationSize": 20,
        }

    def get_filter_schema(self, user):
        return {
            "status": {
                "label": "Status",
                "handler": lambda qs, val: qs.filter(status=val),
            },
            # add more filters here
        }