# from django.db.models import Count
# from django.urls import reverse
#
# from apps.blocks.block_types.chart.chart_block import (
#     BarChartBlock,
#     DonutChartBlock,
#     LineChartBlock,
# )
# from apps.common.models import ProductionOrder
# from plotly import graph_objects as go
#
# class _StatusFilterMixin:
#     """Provide a reusable status filter schema for chart blocks."""
#
#     def _status_filter_schema(self):
#         def status_choices(user, query=""):
#             qs = ProductionOrder.objects.all()
#             qs = self.filter_queryset(user, qs)
#             if query:
#                 qs = qs.filter(status__icontains=query)
#             statuses = (
#                 qs.order_by("status")
#                 .values_list("status", flat=True)
#                 .distinct()
#             )
#             return [(s, s) for s in statuses if s]
#
#         return {
#             "status": {
#                 "label": "Status",
#                 "type": "multiselect",
#                 "multiple": True,
#                 "choices": status_choices,
#                 "choices_url": reverse(
#                     "block_filter_choices", args=[self.block_name, "status"]
#                 ),
#                 "model": ProductionOrder,
#                 "field": "status",
#                 "tom_select_options": {
#                     "placeholder": "Search status...",
#                     "plugins": ["remove_button"],
#                 },
#             }
#         }
#
#
# class ProductionOrdersByStatusChart(_StatusFilterMixin, DonutChartBlock):
#     """Donut chart showing counts of production orders by status."""
#
#     def __init__(self):
#         super().__init__("prod_orders_by_status")
#
#     def get_filter_schema(self, request):
#         return self._status_filter_schema()
#
#     def get_chart_data(self, user, filters):
#         qs = self.filter_queryset(user, ProductionOrder.objects.all())
#         statuses = filters.get("status")
#         if statuses:
#             qs = qs.filter(status__in=statuses)
#         data = (
#             qs.values("status")
#             .order_by("status")
#             .annotate(count=Count("id"))
#         )
#         return {
#             "labels": [row["status"] for row in data],
#             "values": [row["count"] for row in data],
#         }
#
#
# class ProductionOrdersPerItemBarChart(_StatusFilterMixin, BarChartBlock):
#     """Bar chart of production order counts per item."""
#
#     def __init__(self):
#         super().__init__(
#             "prod_orders_per_item_bar",
#             default_layout={
#                 "xaxis": {"title": "Item"},
#                 "yaxis": {"title": "Production Orders"},
#             },
#         )
#
#     def get_bar_trace_overrides(self, user):
#         return {"marker_color": "#ff9900"}
#
#     def get_filter_schema(self, request):
#         return self._status_filter_schema()
#
#     def get_chart_data(self, user, filters):
#         qs = self.filter_queryset(user, ProductionOrder.objects.all())
#         statuses = filters.get("status")
#         if statuses:
#             qs = qs.filter(status__in=statuses)
#         data = (
#             qs.values("item__code")
#             .order_by("item__code")
#             .annotate(count=Count("id"))
#         )
#         return {
#             "x": [row["item__code"] for row in data],
#             "y": [row["count"] for row in data],
#         }
#
#
# class ProductionOrdersPerItemLineChart(_StatusFilterMixin, LineChartBlock):
#     """Line chart of production order counts per item."""
#
#     def __init__(self):
#         super().__init__(
#             "prod_orders_per_item_line",
#             default_layout={
#                 "xaxis": {"title": "Item"},
#                 "yaxis": {"title": "Production Orders"},
#             },
#         )
#
#     def get_filter_schema(self, request):
#         return self._status_filter_schema()
#
#     def get_chart_data(self, user, filters):
#         qs = self.filter_queryset(user, ProductionOrder.objects.all())
#         statuses = filters.get("status")
#         if statuses:
#             qs = qs.filter(status__in=statuses)
#         data = (
#             qs.values("item__code")
#             .order_by("item__code")
#             .annotate(count=Count("id"))
#         )
#         return {
#             "x": [row["item__code"] for row in data],
#             "y": [row["count"] for row in data],
#         }
#
#
# __all__ = [
#     "ProductionOrdersByStatusChart",
#     "ProductionOrdersPerItemBarChart",
#     "ProductionOrdersPerItemLineChart",
# ]
#
from django.urls import reverse

from apps.blocks.block_types.chart.dial_block import DialChartBlock
from apps.common.models import BusinessPartner
from apps.common.models.receipts import ReceiptLine, PurchaseSettings
from django.db.models import Count, Q


class PurchaseOtdDialChart(DialChartBlock):
    """Dial chart showing OTD% over a period, optionally filtered by supplier.

    OTD% = 100 * count(classification.counts_for_ontime=True) / count(all)
    """

    def __init__(self):
        super().__init__("purchase_otd_dial")

    def get_filter_schema(self, request):
        def supplier_choices(user, query=""):
            qs = BusinessPartner.objects.all()
            if query:
                qs = qs.filter(name__icontains=query)
            return [(bp.id, f"{bp.code} - {bp.name}".strip(" -")) for bp in qs.order_by("code")[:50]]

        return {
            "supplier": {
                "label": "Supplier",
                "type": "select",
                "choices": supplier_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "supplier"]),
            },
            "receipt_date_from": {
                "label": "Receipt From",
                "type": "date",
            },
            "receipt_date_to": {
                "label": "Receipt To",
                "type": "date",
            },
        }

    # Allow repeaters to enumerate distinct group values from receipt lines
    def get_enumeration_queryset(self, user):
        return ReceiptLine.objects.all()

    def _apply_filters(self, qs, filters):
        supplier = filters.get("supplier")
        if supplier:
            try:
                supplier_id = int(supplier)
                qs = qs.filter(po_line__order__supplier_id=supplier_id)
            except Exception:
                pass
        f = filters.get("receipt_date_from")
        t = filters.get("receipt_date_to")
        if f:
            qs = qs.filter(receipt_date__gte=f)
        if t:
            qs = qs.filter(receipt_date__lte=t)
        return qs

    def get_value(self, user, filters) -> float:
        qs = ReceiptLine.objects.all()
        qs = self._apply_filters(qs, filters)
        total = qs.count()
        if total == 0:
            return 0.0
        ontime = qs.filter(classification__counts_for_ontime=True).count()
        return round((ontime / total) * 100.0, 2)

    def get_target(self, user, filters) -> float:
        settings = PurchaseSettings.objects.first()
        return float(getattr(settings, "otd_target_percent", 95) or 95)

    # Expose OTD% as a per-group metric for repeaters
    # Returns mapping: { group_value: otd_percent_float }
    def get_repeater_metrics(self, user, group_by: str, base_qs, metric_filters: dict | None = None):
        qs = base_qs
        metric_filters = metric_filters or {}
        f = metric_filters.get("receipt_date_from")
        t = metric_filters.get("receipt_date_to")
        if f:
            qs = qs.filter(receipt_date__gte=f)
        if t:
            qs = qs.filter(receipt_date__lte=t)
        data = (
            qs.values(group_by)
            .annotate(
                total=Count("id"),
                ontime=Count("id", filter=Q(classification__counts_for_ontime=True)),
            )
        )
        out = {}
        for r in data:
            total = r.get("total") or 0
            ontime = r.get("ontime") or 0
            pct = round((ontime / total) * 100.0, 2) if total else 0.0
            out[r.get(group_by)] = pct
        return out


__all__ = [
    "PurchaseOtdDialChart",
]
