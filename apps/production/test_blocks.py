from django.test import TestCase
import django

django.setup()

from django_bi.blocks.registry import block_registry
from apps.production.blocks import ProductionOrderTableBlock
from unittest.mock import MagicMock


class ProductionOrderTableBlockTests(TestCase):
    def setUp(self):
        self.block = ProductionOrderTableBlock()

    def test_block_registry_contains_production_table(self):
        """The production table should be discoverable via the global registry."""

        registered = block_registry.get("production_order_table")
        self.assertIsInstance(registered, ProductionOrderTableBlock)

    def test_filter_schema_includes_item_multiselect(self):
        schema = self.block.get_filter_schema(None)
        item_cfg = schema.get("item")
        self.assertIsNotNone(item_cfg)
        self.assertEqual(item_cfg.get("type"), "multiselect")
        self.assertTrue(item_cfg.get("multiple"))

    def test_item_filter_includes_tom_select_options(self):
        schema = self.block.get_filter_schema(None)
        opts = schema["item"].get("tom_select_options")
        self.assertIsNotNone(opts)
        self.assertEqual(opts.get("placeholder"), "Search items...")
        self.assertIn("remove_button", opts.get("plugins", []))

    def test_item_filter_handler_filters_queryset(self):
        schema = self.block.get_filter_schema(None)
        handler = schema["item"]["handler"]
        qs = MagicMock()
        result = handler(qs, ["ITEM1"])
        qs.filter.assert_called_once_with(item__code__in=["ITEM1"])
        self.assertEqual(result, qs.filter.return_value)
