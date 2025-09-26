from apps.purchase.blocks.tables import *
from apps.purchase.blocks.pivots import *
from apps.purchase.blocks.dials import *
from apps.purchase.blocks.charts import *


def register(registry):
    registry.register("open_purchase_order_lines_table", OpenPurchaseOrderLinesTable())
    registry.register("purchase_order_lines_table", PurchaseOrderLinesTable())
    registry.register("receipt_lines_table", ReceiptLinesTable())

    registry.register("open_purchase_order_lines_pivot", OpenPurchaseOrderLinesPivot())

    registry.register("supplier_otd_dial", SupplierOtdDial())
    registry.register("late_receiving_date_per_buyer_pie", LateReceivingDatePerBuyerPie())
    registry.register("open_po_amount_per_month_bar", OpenPoAmountPerMonthBar())
