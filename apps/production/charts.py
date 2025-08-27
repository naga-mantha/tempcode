from apps.blocks.block_types.chart.chart_block import DonutChartBlock, BarChartBlock, LineChartBlock
from django.urls import reverse

class ProductionOrdersByStatusChart(DonutChartBlock):
    def __init__(self):
        super().__init__(
            "prod_orders_by_status",
            default_layout={}
        )

    def get_filter_schema(self, request):
        # No filters for now
        return {}

    def get_chart_data(self, user, filters):
        # Hardcoded numbers
        return {
            "labels": ["Open", "In Progress", "Closed"],
            "values": [12, 7, 5],
        }

class SalesByMonthChart(BarChartBlock):
    def __init__(self):
        super().__init__(
            block_name="sales_by_month",
            default_layout={"title": "Sales by Month", "margin": {"t": 40}}
        )

    def get_filter_schema(self, user):
        def order_choices(user, query=""):
            return [("all", "All"), ("na", "North America"), ("eu", "Europe")],


        # Fake region selector; not used in the static data
        return {
            "region": {
                "label": "Region",
                "type": "select",
                "choices": order_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "production_order"]),
                # "handler": lambda qs, val: qs.filter(production_order=val) if val else qs,
                "tom_select_options": {
                    "placeholder": "Search regions...",
                },
            },
        }

    def get_chart_data(self, user, filters):
        # Ignore filters for now; return static fake data
        return {
            "x": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "y": [120, 90, 150, 80, 170, 130],
        }


class ActiveUsersOverTimeChart(LineChartBlock):
    def __init__(self):
        super().__init__(
            block_name="active_users_over_time",
            default_layout={
                "title": "Active Users Over Time",
                "xaxis": {"title": "Date"},
                "yaxis": {"title": "Active Users"},
                "margin": {"t": 40},
            },
        )

    def get_filter_schema(self, user):
        # Optional filter; not used by static data
        return {
            "timeframe": {
                "type": "select",
                "label": "Timeframe",
                "choices": [("30d", "Last 30 days"), ("90d", "Last 90 days")],
            }
        }

    def get_chart_data(self, user, filters):
        # Ignore filters for now; return static data
        return {
            "x": ["2025-07-01", "2025-07-08", "2025-07-15", "2025-07-22", "2025-07-29", "2025-08-05"],
            "y": [110, 125, 120, 140, 135, 150],
        }
