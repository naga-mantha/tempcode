from django_bi.conf import settings
from django.db.models import QuerySet
from django.utils.text import slugify

from django_bi.permissions.checks import (
    can_change_instance,
    can_delete_instance,
    can_view_instance,
    can_read_field,
    can_write_field,
    has_perm_cached,
)


def _has_workflow_state_field(model) -> bool:
    try:
        model._meta.get_field("workflow_state")
        return True
    except Exception:
        return False

def _bypass_all(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    staff_bypass = getattr(settings, "PERMISSIONS_STAFF_BYPASS", True)
    return staff_bypass and getattr(user, "is_staff", False)


def get_workflow_state(obj):
    return getattr(obj, "workflow_state", None)

# --------------------------------
# FIELD-LEVEL CHECKS AT STATE
# --------------------------------
def _state_code(state) -> str | None:
    if not state:
        return None
    return slugify(state.name)


def _get_field_perm_codename(model, field_name, state, action):
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{field_name}_{_state_code(state)}"

def can_read_field_state(user, model, field_name, instance=None):
    state = getattr(instance, "workflow_state", None)

    if _bypass_all(user):
        return True

    if not can_read_field(user, model, field_name, instance):
        return False

    if instance and state:
        return has_perm_cached(user, _get_field_perm_codename(model, field_name, state, "view"))

    return True

def can_write_field_state(user, model, field_name, instance=None):
    state = getattr(instance, "workflow_state", None)

    if _bypass_all(user):
        return True

    if not can_write_field(user, model, field_name, instance):
        return False

    if instance and state:
        return has_perm_cached(user, _get_field_perm_codename(model, field_name, state, "change"))

    return True

def get_readable_fields_state(user, model, instance=None):
    fields = [
        f
        for f in list(model._meta.fields) + list(model._meta.many_to_many)
        if not f.auto_created and f.editable
    ]
    if _bypass_all(user):
        return [f.name for f in fields]
    return [f.name for f in fields if can_read_field_state(user, model, f.name, instance)]

def get_editable_fields_state(user, model, instance=None):
    fields = [
        f
        for f in list(model._meta.fields) + list(model._meta.many_to_many)
        if not f.auto_created and f.editable
    ]
    if _bypass_all(user):
        return [f.name for f in fields]
    return [f.name for f in fields if can_write_field_state(user, model, f.name, instance)]

# --------------------------------
# INSTANCE-LEVEL CHECKS AT STATE
# --------------------------------
def _get_instance_perm_codename(instance, action):
    state = getattr(instance, "workflow_state", None)
    if not state:
        return None
    model = instance._meta.model
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{_state_code(state)}"

def can_view_instance_state(user, instance):
    if _bypass_all(user):
        return True
    if not can_view_instance(user, instance):
        return False
    code = _get_instance_perm_codename(instance, "view")
    if not code:
        return True
    return has_perm_cached(user, code)

def can_change_instance_state(user, instance):
    if _bypass_all(user):
        return True
    if not can_change_instance(user, instance):
        return False
    code = _get_instance_perm_codename(instance, "change")
    if not code:
        return True
    return has_perm_cached(user, code)

def can_delete_instance_state(user, instance):
    if _bypass_all(user):
        return True
    if not can_delete_instance(user, instance):
        return False
    code = _get_instance_perm_codename(instance, "delete")
    if not code:
        return True
    return has_perm_cached(user, code)

def _filter_queryset_by_action_state(user, queryset: QuerySet, check_func, *, chunk_size: int = 2000) -> QuerySet:
    if _bypass_all(user):
        return queryset
    # Skip state filtering entirely if model has no workflow_state field
    if not _has_workflow_state_field(queryset.model):
        return queryset
    allowed_qs = queryset.none()
    batch: list[int] = []
    for obj in queryset.select_related("workflow_state").iterator(chunk_size=chunk_size):
        if check_func(user, obj):
            batch.append(obj.pk)
        if len(batch) >= chunk_size:
            allowed_qs |= queryset.filter(pk__in=batch)
            batch.clear()
    if batch:
        allowed_qs |= queryset.filter(pk__in=batch)
    return allowed_qs


def filter_viewable_queryset_state(user, queryset: QuerySet, *, chunk_size: int = 2000):
    return _filter_queryset_by_action_state(user, queryset, can_view_instance_state, chunk_size=chunk_size)

def filter_editable_queryset_state(user, queryset: QuerySet, *, chunk_size: int = 2000):
    return _filter_queryset_by_action_state(user, queryset, can_change_instance_state, chunk_size=chunk_size)

def filter_deletable_queryset_state(user, queryset: QuerySet, *, chunk_size: int = 2000):
    return _filter_queryset_by_action_state(user, queryset, can_delete_instance_state, chunk_size=chunk_size)
