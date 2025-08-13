# apps/permissions/checks.py

from django.db.models import QuerySet

# --------------------
# MODEL-LEVEL CHECKS
# --------------------

def can_act_on_model(user, model, action):
    if user.is_superuser or user.is_staff:
        return True
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return user.has_perm(f"{app_label}.{action}_{model_name}")


def can_view_model(user, model):
    return can_act_on_model(user, model, "view")


def can_add_model(user, model):
    return can_act_on_model(user, model, "add")


def can_change_model(user, model):
    return can_act_on_model(user, model, "change")


def can_delete_model(user, model):
    return can_act_on_model(user, model, "delete")

# ------------------------
# INSTANCE-LEVEL CHECKS
# ------------------------

def can_view_instance(user, instance):
    model = type(instance)
    if user.is_superuser or user.is_staff:
        return True
    if not can_view_model(user, model):
        return False
    if hasattr(instance, "can_user_view"):
        return instance.can_user_view(user)
    return True

def can_change_instance(user, instance):
    model = type(instance)
    if user.is_superuser or user.is_staff:
        return True
    if not can_change_model(user, model):
        return False
    if hasattr(instance, "can_user_change"):
        return instance.can_user_change(user)
    return True

def can_delete_instance(user, instance):
    model = type(instance)
    if user.is_superuser or user.is_staff:
        return True
    if not can_delete_model(user, model):
        return False
    if hasattr(instance, "can_user_delete"):
        return instance.can_user_delete(user)
    return True

# --------------------
# FIELD-LEVEL CHECKS
# --------------------

def _get_perm_codename(model, field_name, action):
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{field_name}"

def can_read_field(user, model, field_name, instance=None):
    if user.is_superuser or user.is_staff:
        return True
    if not can_view_model(user, model):
        return False
    if instance and not can_view_instance(user, instance):
        return False
    return user.has_perm(_get_perm_codename(model, field_name, "view"))

def can_write_field(user, model, field_name, instance=None):
    if user.is_superuser or user.is_staff:
        return True
    if not can_change_model(user, model):
        return False
    if instance and not can_change_instance(user, instance):
        return False
    return user.has_perm(_get_perm_codename(model, field_name, "change"))

def get_readable_fields(user, model, instance=None):
    return [
        field.name
        for field in model._meta.fields
        if can_read_field(user, model, field.name, instance)
    ]

def get_editable_fields(user, model, instance=None):
    return [
        field.name
        for field in model._meta.fields
        if can_write_field(user, model, field.name, instance)
    ]

# ----------------------------------------
# INSTANCE-LEVEL QUERYSET FILTER UTILITIES
# ----------------------------------------

def filter_viewable_queryset(user, queryset: QuerySet):
    """
    Returns only the objects the user is allowed to view.
    """
    objs = list(queryset)

    if user.is_superuser or user.is_staff:
        return objs

    return [obj for obj in objs if can_view_instance(user, obj)]

def filter_editable_queryset(user, queryset: QuerySet):
    """
    Returns only the objects the user is allowed to edit.
    """
    objs = list(queryset)

    if user.is_superuser or user.is_staff:
        return objs

    return [obj for obj in objs if can_change_instance(user, obj)]

def filter_deletable_queryset(user, queryset: QuerySet):
    """
    Returns only the objects the user is allowed to delete.
    """
    objs = list(queryset)

    if user.is_superuser or user.is_staff:
        return objs

    return [obj for obj in objs if can_delete_instance(user, obj)]
