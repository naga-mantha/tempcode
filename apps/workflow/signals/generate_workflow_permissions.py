from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.workflow.utils import generate_workflow_permissions_for_model


@receiver(post_migrate, dispatch_uid="apps.workflow.generate_workflow_permissions")
def generate_workflow_permissions(sender: AppConfig | None, **kwargs):
    """Create per-state instance/field permissions for models in this app."""

    if not isinstance(sender, AppConfig):
        return

    for model in sender.get_models():
        generate_workflow_permissions_for_model(model)
