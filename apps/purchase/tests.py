from django.test import TestCase

from apps.django_bi.blocks.registry import block_registry


class PurchaseBlockRegistryTests(TestCase):
    def test_purchase_table_blocks_registered(self):
        """Verify that purchase dashboards register their block implementations."""

        for block_name in [
            "open_purchase_order_lines_table",
            "purchase_order_lines_table",
            "receipt_lines_table",
        ]:
            with self.subTest(block=block_name):
                self.assertIsNotNone(block_registry.get(block_name))

    def test_purchase_visual_blocks_registered(self):
        visual_blocks = [
            "open_purchase_order_lines_pivot",
            "supplier_otd_dial",
            "late_receiving_date_per_buyer_pie",
            "late_receiving_date_per_supplier_pie",
            "mrp_messages_per_buyer_pie",
            "open_po_amount_per_month_bar",
        ]

        for block_name in visual_blocks:
            with self.subTest(block=block_name):
                self.assertIsNotNone(block_registry.get(block_name))
