from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import PlannedPurchaseOrder

class PlannedPurchaseOrdersPivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("planned_purchase_orders_pivot")

    def get_model(self):
        return PlannedPurchaseOrder
