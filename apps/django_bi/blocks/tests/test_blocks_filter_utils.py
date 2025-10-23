from datetime import date
from unittest import mock

from django.http import QueryDict
from django.test import SimpleTestCase, override_settings

from apps.django_bi.blocks.services.blocks_filter_utils import FilterResolutionMixin


class FilterResolutionMixinFiscalYearTests(SimpleTestCase):
    def test_fiscal_year_start_uses_settings(self):
        qd = QueryDict("filters.start=__current_fiscal_year_start__")
        schema = {"start": {"type": "date"}}

        class FixedDate(date):
            @classmethod
            def today(cls):
                return cls(2024, 3, 15)

        with override_settings(
            BI_FISCAL_YEAR_START_MONTH=7,
            BI_FISCAL_YEAR_START_DAY=1,
        ):
            with mock.patch(
                "apps.django_bi.blocks.services.blocks_filter_utils.date", FixedDate
            ):
                values = FilterResolutionMixin._collect_filters(qd, schema)

        self.assertEqual(values["start"], "2023-07-01")

    def test_fiscal_year_end_uses_settings(self):
        qd = QueryDict("filters.end=__current_fiscal_year_end__")
        schema = {"end": {"type": "date"}}

        class FixedDate(date):
            @classmethod
            def today(cls):
                return cls(2024, 7, 2)

        with override_settings(
            BI_FISCAL_YEAR_START_MONTH=4,
            BI_FISCAL_YEAR_START_DAY=10,
        ):
            with mock.patch(
                "apps.django_bi.blocks.services.blocks_filter_utils.date", FixedDate
            ):
                values = FilterResolutionMixin._collect_filters(qd, schema)

        self.assertEqual(values["end"], "2025-04-09")
