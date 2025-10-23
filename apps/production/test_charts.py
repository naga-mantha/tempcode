from django.test import TestCase
import django

django.setup()

from django_bi.blocks.registry import block_registry
from apps.production.charts import (
    ProductionOrdersByStatusChart,
    ProductionOrdersPerItemBarChart,
    ProductionOrdersPerItemLineChart,
)
from apps.common.models import ProductionOrder, Item
from apps.accounts.models.custom_user import CustomUser


class ProductionChartsTests(TestCase):
    def setUp(self):
        self.status_chart = ProductionOrdersByStatusChart()
        self.bar_chart = ProductionOrdersPerItemBarChart()
        self.line_chart = ProductionOrdersPerItemLineChart()
        self.user = CustomUser.objects.create(username="tester", is_superuser=True)

        item1 = Item.objects.create(code="ITM1")
        item2 = Item.objects.create(code="ITM2")

        ProductionOrder.objects.create(
            production_order="PO1", status="open", item=item1
        )
        ProductionOrder.objects.create(
            production_order="PO2", status="open", item=item1
        )
        ProductionOrder.objects.create(
            production_order="PO3", status="closed", item=item2
        )

    def test_status_filter_schema_is_multiselect(self):
        schema = self.status_chart.get_filter_schema(None)
        cfg = schema.get("status")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("type"), "multiselect")

    def test_donut_chart_counts_by_status(self):
        data = self.status_chart.get_chart_data(self.user, {})
        self.assertEqual(data["labels"], ["closed", "open"])
        self.assertEqual(data["values"], [1, 2])

    def test_bar_chart_filters_by_status(self):
        data = self.bar_chart.get_chart_data(self.user, {"status": ["open"]})
        self.assertEqual(data["x"], ["ITM1"])
        self.assertEqual(data["y"], [2])

    def test_line_chart_returns_all_items(self):
        data = self.line_chart.get_chart_data(self.user, {})
        self.assertEqual(data["x"], ["ITM1", "ITM2"])
        self.assertEqual(data["y"], [2, 1])

    def test_charts_registered_in_block_registry(self):
        self.assertIsInstance(
            block_registry.get("prod_orders_by_status"),
            ProductionOrdersByStatusChart,
        )
        self.assertIsInstance(
            block_registry.get("prod_orders_per_item_bar"),
            ProductionOrdersPerItemBarChart,
        )
        self.assertIsInstance(
            block_registry.get("prod_orders_per_item_line"),
            ProductionOrdersPerItemLineChart,
        )

