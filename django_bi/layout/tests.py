from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from django_bi.blocks.models.block import Block
from django_bi.blocks.models.block_filter_config import BlockFilterConfig
from django_bi.layout.models import Layout, LayoutFilterConfig


class LayoutModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="layout-user")

    def test_layout_slug_and_uniqueness_per_user(self):
        layout = Layout.objects.create(name="Finance Dashboard", user=self.user)
        self.assertEqual(layout.slug, "finance-dashboard")

        with self.assertRaises(IntegrityError):
            Layout.objects.create(name="Finance Dashboard", user=self.user)
        transaction.set_rollback(False)

        other_user = get_user_model().objects.create_user(username="other-user")
        duplicate_name_layout = Layout.objects.create(
            name="Finance Dashboard", user=other_user
        )
        self.assertEqual(duplicate_name_layout.slug, "finance-dashboard")

    def test_layout_filter_config_default_behaviour(self):
        layout = Layout.objects.create(name="Defaulted", user=self.user)

        first = LayoutFilterConfig.objects.create(layout=layout, user=self.user, name="first")
        self.assertTrue(first.is_default)

        second = LayoutFilterConfig.objects.create(
            layout=layout, user=self.user, name="second", is_default=False
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(first.is_default)
        self.assertFalse(second.is_default)

        second.is_default = True
        second.save()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

        second.delete()
        first.refresh_from_db()
        self.assertTrue(first.is_default)


class BlockFilterConfigTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="block-user")
        self.block = Block.objects.create(code="test-block", name="Test Block")

    def test_block_filter_config_default_behaviour(self):
        first = BlockFilterConfig.objects.create(block=self.block, user=self.user, name="first")
        self.assertTrue(first.is_default)

        second = BlockFilterConfig.objects.create(
            block=self.block, user=self.user, name="second", is_default=True
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

        second.delete()
        first.refresh_from_db()
        self.assertTrue(first.is_default)

    def test_block_filter_config_name_unique_per_user_and_block(self):
        BlockFilterConfig.objects.create(block=self.block, user=self.user, name="summary")
        with self.assertRaises(IntegrityError):
            BlockFilterConfig.objects.create(block=self.block, user=self.user, name="summary")
