from apps.blocks.block_types.table.table_block import TableBlock
from apps.common.models import PlannedPurchaseOrder

class PlannedPurchaseOrdersTable(TableBlock):
    def __init__(self):
        super().__init__("planned_purchase_orders_table")

    def get_model(self):
        return PlannedPurchaseOrder

    def get_filter_schema(self, request):
        return {}
