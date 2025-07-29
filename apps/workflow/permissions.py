from .models import StateFieldPermission
from apps.permissions.checks import can_read_field
from apps.permissions.checks import can_write_field

def get_workflow_state(obj):
    return getattr(obj, "workflow_state", None)


def can_read_field_state(obj, field, user):
    # Step 1: check base model+field permission
    if not can_read_field(obj, field, user):
        return False

    # Step 2: check workflow state field permission
    state = get_workflow_state(obj)
    if not state:
        return False  # or True if you prefer fallback allow

    try:
        perm = StateFieldPermission.objects.get(
            workflow=obj.workflow,
            state=state,
            field_name=field
        )
        return user.groups.filter(id__in=perm.can_read.values_list("id", flat=True)).exists()
    except StateFieldPermission.DoesNotExist:
        return False


def can_write_field_state(obj, field, user):
    # Step 1: check base model+field permission
    if not can_write_field(obj, field, user):
        return False

    # Step 2: check workflow state field permission
    state = get_workflow_state(obj)
    if not state:
        return False

    try:
        perm = StateFieldPermission.objects.get(
            workflow=obj.workflow,
            state=state,
            field_name=field
        )
        return user.groups.filter(id__in=perm.can_write.values_list("id", flat=True)).exists()
    except StateFieldPermission.DoesNotExist:
        return False