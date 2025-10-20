from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.blocks.models.block import Block
from apps.blocks.models.layout import Layout
from apps.blocks.models.layout_block import LayoutBlock
from apps.blocks.services.layouts import (
    DEFAULT_GRID_HEIGHT,
    DEFAULT_GRID_WIDTH,
    LayoutGridstackSerializer,
    get_grid_settings,
)


class LayoutGridstackSerializerTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="serializer", email="serializer@example.com", password="pass"
        )
        self.layout = Layout.objects.create(
            owner=self.user,
            name="Dashboard",
            slug="dashboard",
        )
        self.block = Block.objects.create(code="demo.block", name="Demo Block")

    def test_create_new_layout_block(self) -> None:
        serializer = LayoutGridstackSerializer(self.layout)
        serializer.save(
            [
                {
                    "spec_id": "demo.block",
                    "title": "Demo",
                    "x": 2,
                    "y": 3,
                    "width": 5,
                    "height": 4,
                    "configuration": {"foo": "bar"},
                }
            ]
        )

        block = LayoutBlock.objects.get(layout=self.layout)
        self.assertEqual(block.slug, "demo-block")
        self.assertEqual(block.column_index, 2)
        self.assertEqual(block.row_index, 3)
        self.assertEqual(block.configuration["grid"]["width"], 5)
        self.assertEqual(block.configuration["grid"]["height"], 4)
        self.assertEqual(block.configuration["foo"], "bar")

    def test_duplicate_slug_generates_unique_suffix(self) -> None:
        LayoutBlock.objects.create(
            layout=self.layout,
            block=self.block,
            slug="demo-block",
        )

        serializer = LayoutGridstackSerializer(self.layout)
        serializer.save([
            {
                "spec_id": "demo.block",
                "title": "Another",
                "width": 2,
                "height": 2,
            }
        ])

        self.assertTrue(
            LayoutBlock.objects.filter(layout=self.layout, slug="demo-block-2").exists()
        )

    def test_updates_existing_block_without_overwriting_missing_fields(self) -> None:
        block = LayoutBlock.objects.create(
            layout=self.layout,
            block=self.block,
            slug="demo-block",
            row_index=0,
            column_index=0,
            configuration={"grid": {"width": 3, "height": 2}},
        )

        serializer = LayoutGridstackSerializer(self.layout)
        serializer.save(
            [
                {
                    "slug": block.slug,
                    "x": 5,
                    "y": 6,
                    "width": 7,
                }
            ]
        )

        block.refresh_from_db()
        self.assertEqual(block.column_index, 5)
        self.assertEqual(block.row_index, 6)
        self.assertEqual(block.configuration["grid"]["width"], 7)
        self.assertEqual(block.configuration["grid"]["height"], 2)

    def test_get_grid_settings_uses_defaults(self) -> None:
        block = LayoutBlock.objects.create(
            layout=self.layout,
            block=self.block,
            slug="demo-block",
        )

        grid = get_grid_settings(block)
        self.assertEqual(grid["width"], DEFAULT_GRID_WIDTH)
        self.assertEqual(grid["height"], DEFAULT_GRID_HEIGHT)
        self.assertEqual(grid["x"], 0)
        self.assertEqual(grid["y"], 0)
