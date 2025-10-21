from apps.django_bi.blocks.block_types.chart.dial_block import DialChartBlock
from apps.django_bi.blocks.services.filtering import apply_filter_registry
from apps.common.models.receipts import ReceiptLine, PurchaseSettings
from apps.common.filters.schemas import (
    supplier_filter,
    date_from_filter,
    date_to_filter,
)

class SupplierOtdDial(DialChartBlock):
    """Dial chart showing OTD% over a period, optionally filtered by supplier.

    OTD% = 100 * count(classification.counts_for_ontime=True) / count(all)
    """

    def __init__(self):
        super().__init__("supplier_otd_dial")

    def get_filter_schema(self, request):
        return {
            "supplier": supplier_filter(self.block_name, "po_line__order__supplier_id"),
            "receipt_date_from": date_from_filter("receipt_date_from", "Receipt From", "receipt_date"),
            "receipt_date_to": date_to_filter("receipt_date_to", "Receipt To", "receipt_date"),
        }

    def get_value(self, user, filters) -> float:
        qs = apply_filter_registry(self.block_name, ReceiptLine.objects.all(), filters, user)
        total = qs.count()
        if total == 0:
            return 0.0
        ontime = qs.filter(classification__counts_for_ontime=True).count()
        return round((ontime / total) * 100.0, 2)

    def get_target(self, user, filters) -> float:
        settings = PurchaseSettings.objects.first()
        return float(getattr(settings, "otd_target_percent", 95) or 95)

