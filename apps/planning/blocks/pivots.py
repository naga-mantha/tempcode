from django_bi.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.common.models import PlannedPurchaseOrder

class PlannedPurchaseOrdersPivot(PivotBlock):
    def __init__(self):
        super().__init__("planned_purchase_orders_pivot")

    def get_model(self):
        return PlannedPurchaseOrder
