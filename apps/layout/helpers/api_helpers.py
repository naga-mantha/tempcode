from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType

from apps.workflow.views.permissions import has_model_permission, has_field_permission
from apps.layout.filter_registry import get_filter_schema


def get_allowed_fields(user, model, action):
    """
    Returns list of field names on the model the user is allowed to perform `action` on.
    This excludes all fields the user has no access to, based on field-level permission.
    """
    instance = model()  # dummy instance just to pass to has_field_permission

    allowed = []
    for field in model._meta.get_fields():
        if not hasattr(field, 'attname'):  # skip related or reverse relations
            continue

        field_name = field.name
        if has_field_permission(user, instance, field_name, action):
            allowed.append(field_name)

    return allowed


def apply_filter_registry(table_name, queryset, filters):
    """
    Applies filters based on the registered filter schema for the table.
    """
    schema = get_filter_schema(table_name)
    for key, config in schema.items():
        if key in filters and filters[key] is not None:
            queryset = config["handler"](queryset, filters[key])
    return queryset


def get_filtered_queryset(user, model, table_name, filters):
    """
    Main utility:
    - Checks model permission
    - Applies registry-based filters
    - Resolves and returns only allowed fields
    Returns: (filtered_queryset, allowed_field_list)
    """
    if not has_model_permission(user, model, "view"):
        raise PermissionDenied(f"You cannot view {model.__name__}")

    qs = model.objects.all()
    qs = apply_filter_registry(table_name, qs, filters)

    allowed_fields = get_allowed_fields(user, model, "view")
    if not allowed_fields:
        raise PermissionDenied("You cannot view any fields of this model.")

    return qs, allowed_fields
