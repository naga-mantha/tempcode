from apps.blocks.block_types.chart.chart_block import BarChartBlock
from apps.blocks.services.filtering import apply_filter_registry
from apps.common.models import PurchaseOrderLine
from apps.common.filters.schemas import (
    purchase_order_category_filter,
    item_type_filter,
    item_group_filter,
    program_filter,
)
from django.db.models import Sum
from django.db.models.functions import TruncMonth, Coalesce
from django.db.models import FloatField, Value


class OpenPoAmountPerMonthBar(BarChartBlock):
    """Bar chart: Sum of amount_home_currency by Report Month (MM-YY) for open PO lines.

    X: Report Date month (final_receive_date truncated to month), formatted MM-YY
    Y: Sum(amount_home_currency)
    Filters: order__category, item__type, item_group, item_program
    """

    def __init__(self):
        super().__init__(
            "open_po_amount_per_month_bar",
            default_layout={
                "xaxis": {"title": "Report Month (MM-YY)"},
                "yaxis": {"title": "Amount (Home Currency)"},
                "margin": {"l": 60, "r": 20, "t": 30, "b": 60},
                "height": 520,
            },
        )

    def get_model(self):
        return PurchaseOrderLine

    def get_base_queryset(self, user):
        # Only open lines; require a report date to group by month
        return PurchaseOrderLine.objects.filter(status="open", final_receive_date__isnull=False)

    def get_filter_schema(self, request):
        return {
            "category": purchase_order_category_filter(self.block_name, "order__category__code"),
            "item_type": item_type_filter(self.block_name, "item__type__code"),
            "item_group": item_group_filter(self.block_name, "item__item_group__code"),
            "program": program_filter(self.block_name, "item__item_group__program__code", label="Program"),
        }

    def get_chart_data(self, user, filters):
        qs = self.get_base_queryset(user)
        qs = apply_filter_registry(self.block_name, qs, filters or {}, user)
        qs = self.filter_queryset(user, qs)
        # Truncate report date to month and sum amounts
        month_annot = TruncMonth("final_receive_date")
        data_qs = (
            qs.annotate(month=month_annot)
            .values("month")
            .order_by("month")
            .annotate(total=Coalesce(Sum("amount_home_currency"), Value(0.0), output_field=FloatField()))
        )
        # Format labels as MM-YY
        def fmt(m):
            try:
                return m.strftime("%m-%y") if m else ""
            except Exception:
                return ""
        x = [fmt(row["month"]) for row in data_qs]
        y = [float(row["total"] or 0.0) for row in data_qs]
        return {"x": x, "y": y}

