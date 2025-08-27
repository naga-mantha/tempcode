from django.test import TestCase
from apps.production.blocks import ProductionOrderTableBlock
from apps.common.models import Item, ProductionOrder


class ProductionOrderTableBlockTests(TestCase):
    def setUp(self):
        self.block = ProductionOrderTableBlock()
        self.item1 = Item.objects.create(code="ITEM1", description="Item 1")
        self.item2 = Item.objects.create(code="ITEM2", description="Item 2")
        ProductionOrder.objects.create(production_order="PO1", item=self.item1)
        ProductionOrder.objects.create(production_order="PO2", item=self.item2)

    def test_filter_schema_includes_item_multiselect(self):
        schema = self.block.get_filter_schema(None)
        item_cfg = schema.get("item")
        self.assertIsNotNone(item_cfg)
        self.assertEqual(item_cfg.get("type"), "multiselect")
        self.assertTrue(item_cfg.get("multiple"))

    def test_item_filter_handler_filters_queryset(self):
        schema = self.block.get_filter_schema(None)
        handler = schema["item"]["handler"]
        qs = ProductionOrder.objects.all()
        filtered = handler(qs, ["ITEM1"])
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().item, self.item1)
