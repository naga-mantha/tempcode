from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.permissions.utils import generate_field_permissions_for_model


@receiver(post_migrate, dispatch_uid="apps.permissions.generate_field_permissions")
def generate_field_permissions(sender: AppConfig | None, **kwargs) -> None:
    """Ensure view/change permissions exist for each model's fields after migrations."""

    if not isinstance(sender, AppConfig):
        return

    for model in sender.get_models():
        generate_field_permissions_for_model(model)

