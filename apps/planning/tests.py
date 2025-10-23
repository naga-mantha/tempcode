from django.test import TestCase

from django_bi.blocks.registry import block_registry


class PlanningBlockRegistryTests(TestCase):
    def test_planning_table_block_registered(self):
        """The planning dashboard blocks should be exposed via the shared registry."""

        self.assertIsNotNone(
            block_registry.get("planned_purchase_orders_table"),
            "Planned purchase order table block should be registered",
        )

    def test_planning_pivot_block_registered(self):
        block = block_registry.get("planned_purchase_orders_pivot")
        self.assertIsNotNone(block)
