from django.db.models import Count

from django_bi.blocks.block_types.chart.chart_block import DonutChartBlock
from django_bi.blocks.services.filtering import apply_filter_registry
from apps.common.models import PurchaseOrderLine
from django_bi.utils.clock import today
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


class MrpMessagesPerBuyerPie(DonutChartBlock):
    """Donut chart of number of MRP Messages grouped by Buyer.

    - Based on `PurchaseOrderLine` rows that have a related `PurchaseMrpMessage`.
    - Groups by `order__buyer` (CustomUser); null buyers are labeled as "Unassigned".
    - Values are counts of MRP messages (1:1 with qualifying PO lines).
    """

    def __init__(self):
        super().__init__(
            "mrp_messages_per_buyer_pie",
            default_layout={
                "legend": {"orientation": "v"},
                "height": 520,
            },
        )

    def get_filter_schema(self, request):
        # Allow filtering by Supplier and PO Category
        return {
            "supplier": supplier_filter(self.block_name, "order__supplier__code"),
            "category": purchase_order_category_filter(self.block_name, "order__category__code"),
        }

    def get_pie_trace_overrides(self, user):
        # Show number(%) format inside slices
        return {
            "textinfo": "none",  # use texttemplate instead of defaults
            "texttemplate": "%{value} (%{percent})",
            "hovertemplate": "%{label}<br>%{value} (%{percent})<extra></extra>",
        }

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        # Only lines that actually have an MRP message associated
        return PurchaseOrderLine.objects.filter(mrp_message__isnull=False)

    def get_chart_data(self, user, filters):
        qs = self.get_base_queryset(user)
        # Apply configured filters (supplier/category)
        qs = apply_filter_registry(self.block_name, qs, filters or {}, user)
        # Enforce permissions visibility
        qs = self.filter_queryset(user, qs)
        data = (
            qs.values("order__buyer__first_name")
            .order_by("order__buyer__first_name")
            .annotate(count=Count("mrp_message"))
        )
        labels = [row["order__buyer__first_name"] or "Unassigned" for row in data]
        values = [row["count"] for row in data]
        return {"labels": labels, "values": values}

