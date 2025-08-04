from apps.permissions.checks import can_read_field, can_write_field, can_view_instance, can_change_instance, can_delete_instance
from django.db.models import QuerySet

def get_workflow_state(obj):
    return getattr(obj, "workflow_state", None)

# --------------------------------
# FIELD-LEVEL CHECKS AT STATE
# --------------------------------
def _get_field_perm_codename(model, instance, field_name, action):
    state = getattr(instance, "workflow_state", None)
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{field_name}_{state.name.lower().replace(' ', '_')}"

def can_read_field_state(user, model, field_name, instance=None):
    if not can_read_field(user, model, field_name, instance):
        return False

    if instance:
        return user.has_perm(_get_field_perm_codename(model, instance, field_name, "view"))

    return True

def can_write_field_state(user, model, field_name, instance=None):
    if not can_write_field(user, model, field_name, instance):
        return False

    if instance:
        return user.has_perm(_get_field_perm_codename(model, instance, field_name, "change"))

    return True

def get_readable_fields_state(user, model, instance=None):
    return [
        field.name
        for field in model._meta.fields
        if can_read_field_state(user, model, field.name, instance)
    ]

def get_editable_fields_state(user, model, instance=None):
    return [
        field.name
        for field in model._meta.fields
        if can_write_field_state(user, model, field.name, instance)
    ]

# --------------------------------
# INSTANCE-LEVEL CHECKS AT STATE
# --------------------------------
def _get_instance_perm_codename(instance, action):
    state = getattr(instance, "workflow_state", None)
    model = instance._meta.model
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{state.name.lower().replace(' ', '_')}"

def can_view_instance_state(user, instance):
    if not can_view_instance(user, instance):
        return False
    return user.has_perm(_get_instance_perm_codename(instance, "view"))

def can_change_instance_state(user, instance):
    if not can_change_instance(user, instance):
        return False
    return user.has_perm(_get_instance_perm_codename(instance, "change"))

def can_delete_instance_state(user, instance):
    if not can_delete_instance(user, instance):
        return False
    return user.has_perm(_get_instance_perm_codename(instance, "delete"))

def filter_viewable_queryset_state(user, queryset: QuerySet):
    if user.is_superuser or user.is_staff:
        return queryset

    qs = queryset.select_related("workflow_state")
    return queryset.filter(
        pk__in=[obj.pk for obj in qs if can_view_instance_state(user, obj)]
    )

def filter_editable_queryset_state(user, queryset: QuerySet):
    if user.is_superuser or user.is_staff:
        return queryset

    qs = queryset.select_related("workflow_state")
    return queryset.filter(
        pk__in=[obj.pk for obj in qs if can_change_instance_state(user, obj)]
    )

def filter_deletable_queryset_state(user, queryset: QuerySet):
    if user.is_superuser or user.is_staff:
        return queryset

    qs = queryset.select_related("workflow_state")
    return queryset.filter(
        pk__in=[obj.pk for obj in qs if can_delete_instance_state(user, obj)]
    )
