from django.db.models import Count

from apps.blocks.block_types.chart.chart_block import DonutChartBlock
from apps.blocks.services.filtering import apply_filter_registry
from apps.common.models import PurchaseOrderLine
from apps.common.utils.clock import today
from apps.common.filters.schemas import (
    supplier_filter,
    purchase_order_category_filter,
)


class LateReceivingDatePerBuyerPie(DonutChartBlock):
    """Donut chart of PO lines with Report Date before today grouped by Buyer.

    - Report Date is the `final_receive_date` on `PurchaseOrderLine`.
    - Groups by `order__buyer` (CustomUser); null buyers are labeled as "Unassigned".
    - Values are counts of PO lines per buyer.
    """

    def __init__(self):
        super().__init__(
            "late_receiving_date_per_buyer_pie",
            default_layout={
                "legend": {"orientation": "v"},
                # Set a comfortable default size; can be changed later
                "height": 520,
            },
        )

    def get_filter_schema(self, request):
        # Supplier and PO Category filters
        return {
            "supplier": supplier_filter(self.block_name, "order__supplier__code"),
            "category": purchase_order_category_filter(self.block_name, "order__category__code"),
        }

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        # Status constrained per current implementation; past-due by Report Date
        return PurchaseOrderLine.objects.filter(
            status="open",
            final_receive_date__isnull=False,
            final_receive_date__lt=today(),
        )

    def get_chart_data(self, user, filters):
        qs = self.get_base_queryset(user)
        # Apply interdependent filters
        qs = apply_filter_registry(self.block_name, qs, filters or {}, user)
        # Enforce permissions/workflow visibility
        qs = self.filter_queryset(user, qs)
        data = (
            qs.values("order__buyer__first_name")
            .order_by("order__buyer__first_name")
            .annotate(count=Count("id"))
        )
        labels = [row["order__buyer__first_name"] or "Unassigned" for row in data]
        values = [row["count"] for row in data]
        return {"labels": labels, "values": values}




class LateReceivingDatePerSupplierPie(DonutChartBlock):
    """Donut chart of PO lines with Report Date before today grouped by Buyer.

    - Report Date is the `final_receive_date` on `PurchaseOrderLine`.
    - Groups by `order__buyer` (CustomUser); null buyers are labeled as "Unassigned".
    - Values are counts of PO lines per buyer.
    """

    def __init__(self):
        super().__init__(
            "late_receiving_date_per_supplier_pie",
            default_layout={
                "legend": {"orientation": "v"},
                # Set a comfortable default size; can be changed later
                "height": 520,
            },
        )

    def get_filter_schema(self, request):
        # Supplier and PO Category filters
        return {
            "supplier": supplier_filter(self.block_name, "order__supplier__code"),
            "category": purchase_order_category_filter(self.block_name, "order__category__code"),
        }

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        # Status constrained per current implementation; past-due by Report Date
        return PurchaseOrderLine.objects.filter(
            status="open",
            final_receive_date__isnull=False,
            final_receive_date__lt=today(),
        )

    def get_chart_data(self, user, filters):
        qs = self.get_base_queryset(user)
        # Apply interdependent filters
        qs = apply_filter_registry(self.block_name, qs, filters or {}, user)
        # Enforce permissions/workflow visibility
        qs = self.filter_queryset(user, qs)
        data = (
            qs.values("order__supplier__name")
            .order_by("order__supplier__name")
            .annotate(count=Count("id"))
        )
        labels = [row["order__supplier__name"] or "Unassigned" for row in data]
        values = [row["count"] for row in data]
        return {"labels": labels, "values": values}

