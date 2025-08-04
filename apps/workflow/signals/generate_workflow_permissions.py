from django.apps import apps as django_apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.workflow.models import Workflow, State

@receiver(post_migrate)
def generate_workflow_permissions(sender, **kwargs):
    """
    Creates view/change/delete instance and view/change field-level permissions per workflow state.
    """
    for model in django_apps.get_models():
        if not hasattr(model, "_meta"):
            continue

        ct = ContentType.objects.get_for_model(model)
        model_name = model._meta.model_name
        verbose_name = model._meta.verbose_name.title()
        app_label = model._meta.app_label

        # Check for workflow
        if not hasattr(model, "workflow") or not hasattr(model, "workflow_state"):
            continue

        # Try to fetch workflow for the model
        workflows = Workflow.objects.filter(content_type=ct)
        for wf in workflows:
            for state in wf.states.all():
                state_code = state.name.lower().replace(" ", "_")

                # Instance-level perms
                perms = {
                    f"view_{model_name}_{state_code}": f'Can view "{verbose_name}" in state "{state.name}"',
                    f"change_{model_name}_{state_code}": f'Can change "{verbose_name}" in state "{state.name}"',
                    f"delete_{model_name}_{state_code}": f'Can delete "{verbose_name}" in state "{state.name}"',
                }

                for codename, name in perms.items():
                    Permission.objects.get_or_create(
                        codename=codename,
                        content_type=ct,
                        defaults={"name": name}
                    )

                # Field-level perms
                for field in model._meta.fields:
                    field_name = field.name
                    perms = {
                        f"view_{model_name}_{field_name}_{state_code}": f'Can view field "{field_name}" on "{verbose_name}" in state "{state.name}"',
                        f"change_{model_name}_{field_name}_{state_code}": f'Can change field "{field_name}" on "{verbose_name}" in state "{state.name}"',
                    }
                    for codename, name in perms.items():
                        Permission.objects.get_or_create(
                            codename=codename,
                            content_type=ct,
                            defaults={"name": name}
                        )
