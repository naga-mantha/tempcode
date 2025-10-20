from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.blocks import registry as block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.layout import Layout, VisibilityChoices
from apps.blocks.models.layout_block import LayoutBlock
from apps.blocks.models.layout_filter_config import LayoutFilterConfig
from apps.blocks.specs import BlockSpec, Services


class SimpleFilterResolver:
    """Minimal resolver used to exercise filter config flows in tests."""

    def __init__(self, spec=None):  # pragma: no cover - signature parity only
        self.spec = spec

    def schema(self):
        return [{"key": "status", "type": "select"}]

    def resolve(self, request):  # pragma: no cover - not exercised
        return {}

    def clean(self, values):
        return values


class LayoutViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.spec_id = "tests.simple"
        cls.services = Services(filter_resolver=SimpleFilterResolver)
        cls.spec = BlockSpec(
            id=cls.spec_id,
            name="Test Block",
            kind="content",
            template="blocks/tests/simple_block.html",
            supported_features=(),
            services=cls.services,
        )
        if cls.spec_id not in block_registry._REGISTRY:  # type: ignore[attr-defined]
            block_registry.register(cls.spec)
        cls.UserModel = get_user_model()

    @classmethod
    def tearDownClass(cls):
        try:
            block_registry._REGISTRY.pop(cls.spec_id, None)  # type: ignore[attr-defined]
        finally:
            super().tearDownClass()

    def setUp(self):
        self.owner = self.UserModel.objects.create_user(
            username="layout-owner",
            email="owner@example.com",
            password="pass",
        )
        self.other_user = self.UserModel.objects.create_user(
            username="other-user",
            email="other@example.com",
            password="pass",
        )
        self.public_user = self.UserModel.objects.create_user(
            username="public-user",
            email="public@example.com",
            password="pass",
            is_staff=True,
        )
        self.staff_user = self.UserModel.objects.create_user(
            username="staffer",
            email="staff@example.com",
            password="pass",
            is_staff=True,
        )
        self.client.force_login(self.owner)
        self.layout = Layout.objects.create(
            owner=self.owner,
            name="Owner Private",
            slug="owner-private",
            visibility=VisibilityChoices.PRIVATE,
        )

    # ------------------------------------------------------------------
    # Layout list ordering
    # ------------------------------------------------------------------
    def test_layout_list_orders_by_ownership_priority_then_name(self):
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff"])
        try:
            Layout.objects.create(
                owner=self.owner,
                name="Owner Public",
                slug="owner-public",
                visibility=VisibilityChoices.PUBLIC,
            )
        finally:
            self.owner.is_staff = False
            self.owner.save(update_fields=["is_staff"])
        other_public = Layout.objects.create(
            owner=self.public_user,
            name="Alpha Other",
            slug="alpha-other",
            visibility=VisibilityChoices.PUBLIC,
        )
        Layout.objects.create(
            owner=self.other_user,
            name="Other Private",
            slug="other-private",
            visibility=VisibilityChoices.PRIVATE,
        )

        response = self.client.get(reverse("blocks:layout_list"))
        self.assertEqual(response.status_code, 200)
        layouts = list(response.context["layouts"])
        self.assertEqual([layout.slug for layout in layouts], [
            "owner-private",
            "owner-public",
            other_public.slug,
        ])

    # ------------------------------------------------------------------
    # Create/edit permissions
    # ------------------------------------------------------------------
    def test_create_view_blocks_public_visibility_for_non_staff(self):
        layout = Layout(
            owner=self.owner,
            name="Unauthorized Public",
            slug="unauthorized-public",
            visibility=VisibilityChoices.PUBLIC,
        )
        with self.assertRaises(ValidationError) as exc:
            layout.full_clean()
        self.assertIn("visibility", exc.exception.message_dict)

    def test_edit_view_enforces_owner_or_staff_permissions(self):
        url = reverse(
            "blocks:layout_edit",
            kwargs={"username": self.layout.owner.username, "slug": self.layout.slug},
        )

        self.client.force_login(self.other_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # HTMX block add/remove
    # ------------------------------------------------------------------
    def test_htmx_block_add_and_remove_flow(self):
        add_url = reverse(
            "blocks:layout_block_add",
            kwargs={"username": self.layout.owner.username, "slug": self.layout.slug},
        )
        payload = {
            "spec_id": self.spec_id,
            "title": "Example Block",
            "x": 1,
            "y": 0,
            "width": 4,
            "height": 3,
            "configuration": {"grid": {"width": 4, "height": 3}},
        }
        response = self.client.post(
            add_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        block = LayoutBlock.objects.get(layout=self.layout)
        self.assertEqual(block.block.code, self.spec_id)
        self.assertIn(block.slug, response.content.decode())

        remove_url = reverse(
            "blocks:layout_block_remove",
            kwargs={
                "username": self.layout.owner.username,
                "slug": self.layout.slug,
                "block_slug": block.slug,
            },
        )
        response = self.client.post(remove_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LayoutBlock.objects.filter(layout=self.layout).exists())

    # ------------------------------------------------------------------
    # Filter config CRUD
    # ------------------------------------------------------------------
    def test_filter_config_crud_endpoints(self):
        block = get_or_create_block(self.spec_id)
        LayoutBlock.objects.create(
            layout=self.layout,
            block=block,
            slug="filter-block",
            configuration={"grid": {"width": 4, "height": 3}},
        )

        save_url = reverse(
            "blocks:layout_filter_config_save",
            kwargs={"username": self.layout.owner.username, "slug": self.layout.slug},
        )
        values = {
            "blocks": {"filter-block": {"filters": {"status": "open"}}},
        }
        response = self.client.post(
            save_url,
            data={
                "name": "Initial Filters",
                "visibility": VisibilityChoices.PRIVATE,
                "is_default": "on",
                "values_json": json.dumps(values),
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        config = LayoutFilterConfig.objects.get(layout=self.layout)
        self.assertTrue(config.is_default)
        self.assertIn("Initial Filters", response.content.decode())

        rename_url = reverse(
            "blocks:layout_filter_config_rename",
            kwargs={
                "username": self.layout.owner.username,
                "slug": self.layout.slug,
                "config_id": config.pk,
            },
        )
        response = self.client.post(
            rename_url,
            data={"name": "Renamed Filters"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        config.refresh_from_db()
        self.assertEqual(config.name, "Renamed Filters")

        duplicate_url = reverse(
            "blocks:layout_filter_config_duplicate",
            kwargs={
                "username": self.layout.owner.username,
                "slug": self.layout.slug,
                "config_id": config.pk,
            },
        )
        response = self.client.post(duplicate_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        copies = LayoutFilterConfig.objects.filter(layout=self.layout)
        self.assertEqual(copies.count(), 2)
        duplicate = copies.exclude(pk=config.pk).get()
        self.assertFalse(duplicate.is_default)
        self.assertNotEqual(duplicate.slug, config.slug)

        make_default_url = reverse(
            "blocks:layout_filter_config_make_default",
            kwargs={
                "username": self.layout.owner.username,
                "slug": self.layout.slug,
                "config_id": duplicate.pk,
            },
        )
        response = self.client.post(make_default_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        config.refresh_from_db()
        duplicate.refresh_from_db()
        self.assertTrue(duplicate.is_default)
        self.assertFalse(config.is_default)

        delete_url = reverse(
            "blocks:layout_filter_config_delete",
            kwargs={
                "username": self.layout.owner.username,
                "slug": self.layout.slug,
                "config_id": duplicate.pk,
            },
        )
        response = self.client.post(delete_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        remaining = LayoutFilterConfig.objects.get(layout=self.layout)
        self.assertTrue(remaining.is_default)
        self.assertEqual(remaining.pk, config.pk)


def get_or_create_block(code: str) -> Block:
    block, _ = Block.objects.get_or_create(code=code, defaults={"name": code})
    return block
