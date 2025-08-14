from django.apps import apps as django_apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.permissions.utils import generate_field_permissions_for_model


@receiver(post_migrate)
def generate_field_permissions(sender, **kwargs):
    """Ensure view/change permissions exist for each model's fields after migrations."""

    for model in django_apps.get_models():
        generate_field_permissions_for_model(model)

