from django.contrib.messages import get_messages
from django.db import IntegrityError
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.db.models import Count
from unittest.mock import patch

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.base import BaseBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.block_types.chart.chart_block import DonutChartBlock
from apps.common.models import ProductionOrder, Item


class BlockFilterConfigTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="user")
        self.block = Block.objects.create(code="block", name="Block")

    def test_unique_constraint_on_block_user_name(self):
        BlockFilterConfig.objects.create(
            block=self.block,
            user=self.user,
            name="default",
            values={"foo": "bar"},
        )

        with self.assertRaises(IntegrityError):
            BlockFilterConfig.objects.create(
                block=self.block,
                user=self.user,
                name="default",
                values={"baz": "qux"},
            )


class FilterConfigViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="user")
        self.block_name = "test_block"
        self.block = Block.objects.create(code=self.block_name, name="Test Block")

        class DummyBlock(BaseBlock):
            def get_config(self, request):
                return {}

            def get_data(self, request):
                return {}

            def get_filter_schema(self, request):
                return {}

        self.dummy_block = DummyBlock()
        self.dummy_block.block_name = self.block_name
        if not block_registry.get(self.block_name):
            block_registry.register(self.block_name, self.dummy_block)

        self.client.force_login(self.user)

    def tearDown(self):
        block_registry._blocks.pop(self.block_name, None)
        block_registry._metadata.pop(self.block_name, None)

    def test_duplicate_name_shows_error_message(self):
        BlockFilterConfig.objects.create(
            block=self.block,
            user=self.user,
            name="existing",
            values={},
        )
        response = self.client.post(
            reverse("table_filter_config", args=[self.block_name]),
            {"name": "existing"},
            follow=True,
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("name already taken" in m.lower() for m in messages),
            messages,
        )
        self.assertEqual(
            BlockFilterConfig.objects.filter(
                block=self.block, user=self.user, name="existing"
            ).count(),
            1,
        )


class ChartFilterConfigViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="user2")
        self.block_name = "chart_block"
        self.block = Block.objects.create(code=self.block_name, name="Chart Block")

        class DummyChart(DonutChartBlock):
            def get_chart_data(self, user, filters):
                return {"labels": ["A"], "values": [1]}

            def get_filter_schema(self, request):
                return {}

        self.block_impl = DummyChart(self.block_name)
        if not block_registry.get(self.block_name):
            block_registry.register(self.block_name, self.block_impl)

        self.client.force_login(self.user)

    def tearDown(self):
        block_registry._blocks.pop(self.block_name, None)
        block_registry._metadata.pop(self.block_name, None)

    def test_duplicate_name_shows_error_message(self):
        BlockFilterConfig.objects.create(
            block=self.block,
            user=self.user,
            name="existing",
            values={},
        )
        response = self.client.post(
            reverse("chart_filter_config", args=[self.block_name]),
            {"name": "existing"},
            follow=True,
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("name already taken" in m.lower() for m in messages),
            messages,
        )
        self.assertEqual(
            BlockFilterConfig.objects.filter(
                block=self.block, user=self.user, name="existing"
            ).count(),
            1,
        )


class ChartBlockFilterResolutionTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="cb-user")
        self.block_name = "dummy_chart"
        self.block = Block.objects.create(code=self.block_name, name="Dummy Chart")

        class DummyChart(DonutChartBlock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.captured_filters = None

            def get_filter_schema(self, request):
                return {"status": {"label": "Status"}}

            def get_chart_data(self, user, filters):
                self.captured_filters = dict(filters)
                return {"labels": [], "values": []}

        self.block_impl = DummyChart(self.block_name)
        block_registry.register(self.block_name, self.block_impl)
        self.factory = RequestFactory()

    def tearDown(self):
        block_registry._blocks.pop(self.block_name, None)
        block_registry._metadata.pop(self.block_name, None)

    def test_filters_resolved_with_namespaced_instance(self):
        instance = "abc123"
        request = self.factory.get(
            "/", {f"{self.block_name}__{instance}__filters.status": "open"}
        )
        request.user = self.user

        # The block should detect the instance namespace and capture the filter value
        self.block_impl.get_data(request)
        self.assertEqual(self.block_impl.captured_filters, {"status": "open"})


class ChartBlockPermissionTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="perm-user")
        self.factory = RequestFactory()

    def test_unreadable_field_removed_from_filter_schema(self):
        class DummyChart(DonutChartBlock):
            def __init__(self):
                super().__init__("dummy_perm_chart")

            def get_filter_schema(self, request):
                return {"status": {"label": "Status", "model": ProductionOrder, "field": "status"}}

            def get_chart_data(self, user, filters):
                return {"labels": [], "values": []}

        chart = DummyChart()
        request = self.factory.get("/")
        request.user = self.user
        with patch("apps.blocks.block_types.chart.chart_block.can_read_field_generic", return_value=False), patch(
            "apps.blocks.block_types.chart.chart_block.can_read_field_state", return_value=False
        ):
            schema, _vals = chart._resolve_filters(request, None)
        self.assertNotIn("status", schema)

    def test_filter_queryset_excludes_unviewable_rows(self):
        item = Item.objects.create(code="ITM1")
        ProductionOrder.objects.create(production_order="PO1", status="open", item=item)
        ProductionOrder.objects.create(production_order="PO2", status="closed", item=item)

        class DummyChart(DonutChartBlock):
            def __init__(self):
                super().__init__("dummy_qs_chart")

            def get_filter_schema(self, request):
                return {}

            def get_chart_data(self, user, filters):
                qs = ProductionOrder.objects.all()
                qs = self.filter_queryset(user, qs)
                data = qs.values("status").order_by("status").annotate(count=Count("id"))
                return {
                    "labels": [row["status"] for row in data],
                    "values": [row["count"] for row in data],
                }

        chart = DummyChart()
        with patch(
            "apps.blocks.block_types.chart.chart_block.filter_viewable_queryset_generic",
            side_effect=lambda user, qs: qs.filter(status="open"),
        ) as mock_generic, patch(
            "apps.blocks.block_types.chart.chart_block.filter_viewable_queryset_state",
            side_effect=lambda user, qs: qs,
        ) as mock_state:
            data = chart.get_chart_data(self.user, {})
            mock_generic.assert_called_once()
            mock_state.assert_called_once()
        self.assertEqual(data["labels"], ["open"])
        self.assertEqual(data["values"], [1])
