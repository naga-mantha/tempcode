from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from types import SimpleNamespace

from apps.permissions.checks import get_editable_fields, get_readable_fields
from apps.permissions.forms import PermissionFormMixin
from apps.permissions.signals.generate_field_permissions import (
    generate_field_permissions,
)


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

