from apps.planning.blocks.tables import *
from apps.planning.blocks.pivots import *

def register(registry):
    registry.register("planned_purchase_orders_table", PlannedPurchaseOrdersTable())

    registry.register("planned_purchase_orders_pivot", PlannedPurchaseOrdersPivot())
