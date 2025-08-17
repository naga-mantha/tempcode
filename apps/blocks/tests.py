from django.contrib.messages import get_messages
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.base import BaseBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.block_types.chart.chart_block import DonutChartBlock


class BlockFilterConfigTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="user")
        self.block = Block.objects.create(name="block")

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
        self.block = Block.objects.create(name=self.block_name)

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
        self.block = Block.objects.create(name=self.block_name)

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
