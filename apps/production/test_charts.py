from django.test import SimpleTestCase
import django

django.setup()

from apps.production.charts import SalesByMonthChart


class SalesByMonthChartTests(SimpleTestCase):
    def setUp(self):
        self.chart = SalesByMonthChart()

    def test_region_filter_has_fixed_choices(self):
        schema = self.chart.get_filter_schema(None)
        region_cfg = schema.get("region")
        self.assertIsNotNone(region_cfg)
        self.assertEqual(region_cfg.get("type"), "select")
        self.assertEqual(
            region_cfg.get("choices"),
            [("all", "All"), ("na", "North America"), ("eu", "Europe")],
        )
        self.assertNotIn("choices_url", region_cfg)
        opts = region_cfg.get("tom_select_options")
        self.assertIsNotNone(opts)
        self.assertFalse(opts.get("create"))
