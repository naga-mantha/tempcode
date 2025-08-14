from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError, call_command
from django.apps import apps as django_apps
from django.db import models
from django.test import SimpleTestCase, TestCase
from types import SimpleNamespace
from unittest.mock import patch

from apps.permissions.checks import get_editable_fields, get_readable_fields
from apps.permissions.forms import PermissionFormMixin
from apps.permissions.signals.generate_field_permissions import (
    generate_field_permissions,
)
from apps.permissions.utils import generate_field_permissions_for_model


User = get_user_model()


class UserForm(PermissionFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "groups"]


class M2MPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Ensure permissions exist for User model fields, including M2M ones
        generate_field_permissions(None)

    def test_generate_permissions_for_m2m_field(self):
        ct = ContentType.objects.get_for_model(User)
        self.assertTrue(
            Permission.objects.filter(
                content_type=ct, codename="view_user_groups"
            ).exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                content_type=ct, codename="change_user_groups"
            ).exists()
        )

    def test_get_fields_includes_m2m(self):
        user = SimpleNamespace(is_superuser=True, is_staff=False, has_perm=lambda p: True)
        self.assertIn("groups", get_readable_fields(user, User))
        self.assertIn("groups", get_editable_fields(user, User))

    def test_permission_form_mixin_handles_m2m(self):
        # User without permissions shouldn't see the field
        user_none = SimpleNamespace(is_superuser=False, is_staff=False, has_perm=lambda p: False)
        form = UserForm(user=user_none)
        self.assertNotIn("groups", form.fields)

        # User with read but not write permission sees disabled field
        def has_perm(perm):
            return perm in {
                "auth.view_user",
                "auth.change_user",
                "auth.view_user_groups",
            }

        user_read_only = SimpleNamespace(is_superuser=False, is_staff=False, has_perm=has_perm)
        form = UserForm(user=user_read_only)
        self.assertIn("groups", form.fields)
        self.assertTrue(form.fields["groups"].disabled)


class FieldFilteringTests(SimpleTestCase):
    def test_non_editable_and_auto_created_fields_skipped(self):
        class DummyModel(models.Model):
            name = models.CharField(max_length=10)
            hidden = models.CharField(max_length=10, editable=False)

            class Meta:
                app_label = "tests"

        class DummyUser:
            is_superuser = False
            is_staff = False

            def __init__(self):
                self.calls = []

            def has_perm(self, perm):
                self.calls.append(perm)
                return True

        user = DummyUser()

        readable = get_readable_fields(user, DummyModel)
        editable = get_editable_fields(user, DummyModel)

        self.assertEqual(readable, ["name"])
        self.assertEqual(editable, ["name"])

        self.assertIn("tests.view_dummymodel_name", user.calls)
        self.assertIn("tests.change_dummymodel_name", user.calls)
        self.assertNotIn("tests.view_dummymodel_id", user.calls)
        self.assertNotIn("tests.view_dummymodel_hidden", user.calls)
        self.assertNotIn("tests.change_dummymodel_id", user.calls)
        self.assertNotIn("tests.change_dummymodel_hidden", user.calls)

class RebuildFieldPermissionsCommandTests(TestCase):
    def test_model_requires_app(self):
        with self.assertRaises(CommandError):
            call_command("rebuild_field_permissions", model="User")

    def test_invalid_app(self):
        with self.assertRaises(CommandError):
            call_command("rebuild_field_permissions", app="invalid")

    def test_invalid_model(self):
        with self.assertRaises(CommandError):
            call_command("rebuild_field_permissions", app="auth", model="Nope")

    @patch(
        "apps.permissions.management.commands.rebuild_field_permissions.generate_field_permissions_for_model",
        return_value=(0, 0),
    )
    def test_specific_model(self, mock_generate):
        call_command("rebuild_field_permissions", app="auth", model="User")
        user_model = django_apps.get_model("auth", "User")
        mock_generate.assert_called_once_with(user_model)

    @patch(
        "apps.permissions.management.commands.rebuild_field_permissions.generate_field_permissions_for_model",
        return_value=(0, 0),
    )
    def test_app_only(self, mock_generate):
        call_command("rebuild_field_permissions", app="auth")
        auth_models = list(django_apps.get_app_config("auth").get_models())
        called_models = [call.args[0] for call in mock_generate.call_args_list]
        self.assertCountEqual(auth_models, called_models)


class FieldPermissionCleanupTests(TestCase):
    def test_deletes_obsolete_field_permissions(self):
        class DummyModel(models.Model):
            name = models.CharField(max_length=10)

            class Meta:
                app_label = "tests"

        # Initial generation to create permissions for existing fields
        generate_field_permissions_for_model(DummyModel)

        ct = ContentType.objects.get_for_model(DummyModel)
        # Create leftover permissions for a removed field
        Permission.objects.create(
            codename="view_dummymodel_old",
            name='Can view field "old" on Model "DummyModel"',
            content_type=ct,
        )
        Permission.objects.create(
            codename="change_dummymodel_old",
            name='Can change field "old" on Model "DummyModel"',
            content_type=ct,
        )

        created, deleted = generate_field_permissions_for_model(DummyModel)

        self.assertEqual(created, 0)
        self.assertEqual(deleted, 2)
        self.assertFalse(
            Permission.objects.filter(
                content_type=ct, codename="view_dummymodel_old"
            ).exists()
        )
        self.assertFalse(
            Permission.objects.filter(
                content_type=ct, codename="change_dummymodel_old"
            ).exists()
        )


class ProxyAndAbstractModelTests(TestCase):
    def test_returns_zero_for_proxy_model(self):
        class Base(models.Model):
            name = models.CharField(max_length=10)

            class Meta:
                app_label = "tests"

        class Proxy(Base):
            class Meta:
                app_label = "tests"
                proxy = True

        with patch(
            "apps.permissions.utils.ContentType.objects.get_for_model"
        ) as mock_get_for_model:
            created, deleted = generate_field_permissions_for_model(Proxy)
        self.assertEqual((created, deleted), (0, 0))
        mock_get_for_model.assert_not_called()

    def test_returns_zero_for_abstract_model(self):
        class Abstract(models.Model):
            name = models.CharField(max_length=10)

            class Meta:
                app_label = "tests"
                abstract = True

        with patch(
            "apps.permissions.utils.ContentType.objects.get_for_model"
        ) as mock_get_for_model:
            created, deleted = generate_field_permissions_for_model(Abstract)
        self.assertEqual((created, deleted), (0, 0))
        mock_get_for_model.assert_not_called()

