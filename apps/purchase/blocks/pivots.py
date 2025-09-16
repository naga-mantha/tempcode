from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import PurchaseOrderLine


class OpenPurchaseOrderLinesPivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("open_purchase_order_lines_pivot")

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        return PurchaseOrderLine.objects.filter(status="open")
