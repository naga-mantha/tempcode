from django.core.exceptions import PermissionDenied
from apps.workflow.views.permissions import get_allowed_fields
from apps.layout.filter_registry import get_filter_schema

def apply_filter_registry(table_name, queryset, filters, user):
    """
    Applies filters based on the registered filter schema for the table.
    """
    schema = get_filter_schema(table_name, user=user)
    for key, config in schema.items():
        if key in filters and filters[key] is not None:
            queryset = config["handler"](queryset, filters[key])
    return queryset


def get_filtered_queryset(user, model, table_name, filters):
    """
    Main utility:
    - Checks Django model-level 'view' permission
    - Applies registry-based filters
    - Resolves and returns only allowed fields

    Returns: (filtered_queryset, allowed_field_list)
    """
    # model-level permission
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    perm_string = f"{app_label}.view_{model_name}"
    if not user.has_perm(perm_string):
        raise PermissionDenied(f"You cannot view {model.__name__}")

    qs = model.objects.all()
    qs = apply_filter_registry(table_name, qs, filters, user=user)

    allowed_fields = get_allowed_fields(user, model, 'view')
    if not allowed_fields:
        raise PermissionDenied("You cannot view any fields of this model.")

    return qs, allowed_fields
