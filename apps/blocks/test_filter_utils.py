from django.test import TestCase
from django.http import QueryDict

from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin


class FilterResolutionMixinTests(TestCase):
    def test_collect_filters_text_single(self):
        qd = QueryDict("filters.customer=5")
        schema = {"customer": {"type": "text", "multiple": False}}
        result = FilterResolutionMixin._collect_filters(qd, schema)
        self.assertEqual(result["customer"], "5")

    def test_collect_filters_multiselect(self):
        qd = QueryDict("filters.item=1&filters.item=2")
        schema = {"item": {"type": "multiselect", "multiple": True, "choices": [("1","One"), ("2","Two")]}}
        result = FilterResolutionMixin._collect_filters(qd, schema)
        self.assertEqual(result["item"], ["1", "2"])
