from django.db.models import Count
from django.urls import reverse

from apps.django_bi.blocks.block_types.chart.chart_block import (
    BarChartBlock,
    DonutChartBlock,
    LineChartBlock,
)
from apps.common.models import ProductionOrder
from plotly import graph_objects as go

class _StatusFilterMixin:
    """Provide a reusable status filter schema for chart blocks."""

    def _status_filter_schema(self):
        def status_choices(user, query=""):
            qs = ProductionOrder.objects.all()
            qs = self.filter_queryset(user, qs)
            if query:
                qs = qs.filter(status__icontains=query)
            statuses = (
                qs.order_by("status")
                .values_list("status", flat=True)
                .distinct()
            )
            return [(s, s) for s in statuses if s]

        return {
            "status": {
                "label": "Status",
                "type": "multiselect",
                "multiple": True,
                "choices": status_choices,
                "choices_url": reverse(
                    "block_filter_choices", args=[self.block_name, "status"]
                ),
                "model": ProductionOrder,
                "field": "status",
                "tom_select_options": {
                    "placeholder": "Search status...",
                    "plugins": ["remove_button"],
                },
            }
        }


class ProductionOrdersByStatusChart(_StatusFilterMixin, DonutChartBlock):
    """Donut chart showing counts of production orders by status."""

    def __init__(self):
        super().__init__("prod_orders_by_status")

    def get_filter_schema(self, request):
        return self._status_filter_schema()

    def get_chart_data(self, user, filters):
        qs = self.filter_queryset(user, ProductionOrder.objects.all())
        statuses = filters.get("status")
        if statuses:
            qs = qs.filter(status__in=statuses)
        data = (
            qs.values("status")
            .order_by("status")
            .annotate(count=Count("id"))
        )
        return {
            "labels": [row["status"] for row in data],
            "values": [row["count"] for row in data],
        }


class ProductionOrdersPerItemBarChart(_StatusFilterMixin, BarChartBlock):
    """Bar chart of production order counts per item."""

    def __init__(self):
        super().__init__(
            "prod_orders_per_item_bar",
            default_layout={
                "xaxis": {"title": "Item"},
                "yaxis": {"title": "Production Orders"},
            },
        )

    def get_bar_trace_overrides(self, user):
        return {"marker_color": "#ff9900"}

    def get_filter_schema(self, request):
        return self._status_filter_schema()

    def get_chart_data(self, user, filters):
        qs = self.filter_queryset(user, ProductionOrder.objects.all())
        statuses = filters.get("status")
        if statuses:
            qs = qs.filter(status__in=statuses)
        data = (
            qs.values("item__code")
            .order_by("item__code")
            .annotate(count=Count("id"))
        )
        return {
            "x": [row["item__code"] for row in data],
            "y": [row["count"] for row in data],
        }


class ProductionOrdersPerItemLineChart(_StatusFilterMixin, LineChartBlock):
    """Line chart of production order counts per item."""

    def __init__(self):
        super().__init__(
            "prod_orders_per_item_line",
            default_layout={
                "xaxis": {"title": "Item"},
                "yaxis": {"title": "Production Orders"},
            },
        )

    def get_filter_schema(self, request):
        return self._status_filter_schema()

    def get_chart_data(self, user, filters):
        qs = self.filter_queryset(user, ProductionOrder.objects.all())
        statuses = filters.get("status")
        if statuses:
            qs = qs.filter(status__in=statuses)
        data = (
            qs.values("item__code")
            .order_by("item__code")
            .annotate(count=Count("id"))
        )
        return {
            "x": [row["item__code"] for row in data],
            "y": [row["count"] for row in data],
        }


__all__ = [
    "ProductionOrdersByStatusChart",
    "ProductionOrdersPerItemBarChart",
    "ProductionOrdersPerItemLineChart",
]

