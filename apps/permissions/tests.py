from django import forms
from django.apps import apps as django_apps
from django.db import models
from django.test import TestCase
from types import SimpleNamespace

from apps.permissions.forms import PermissionFormMixin


class DummyModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "permissions"


django_apps.register_model("permissions", DummyModel)


class DummyForm(PermissionFormMixin, forms.ModelForm):
    class Meta:
        model = DummyModel
        fields = ["name"]


class PermissionFormMixinTest(TestCase):
    def test_instance_binding(self):
        instance = DummyModel(name="foo")
        user = SimpleNamespace(is_superuser=True, is_staff=True, has_perm=lambda perm: True)
        form = DummyForm(user=user, instance=instance)

        self.assertIs(form.instance, instance)
        self.assertEqual(form.initial["name"], "foo")
