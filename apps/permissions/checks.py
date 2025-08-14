# apps/permissions/checks.py

"""Utilities for permission checks.

This module caches calls to :meth:`User.has_perm` for the duration of a
request to avoid repeated permission lookups.  Use
``clear_perm_cache()`` after long‑running tasks (such as management commands
or Celery workers) to avoid stale results or memory growth.  The cache may
also be temporarily disabled with the :func:`disable_perm_cache`
context manager.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from django.db.models import QuerySet


# ---------------------------------
# per-request user.has_perm caching
# ---------------------------------

_perm_cache_var: ContextVar[dict | None] = ContextVar("perm_cache", default=None)
_cache_disabled_var: ContextVar[bool] = ContextVar("perm_cache_disabled", default=False)


def _cached_has_perm(user, perm: str) -> bool:
    """Return ``user.has_perm(perm)`` using a per-request cache."""

    if _cache_disabled_var.get():
        return user.has_perm(perm)

    cache = _perm_cache_var.get()
    if cache is None:
        cache = {}
        _perm_cache_var.set(cache)
    key = (id(user), perm)
    if key not in cache:
        cache[key] = user.has_perm(perm)
    return cache[key]


def clear_perm_cache() -> None:
    """Clear the permission cache.

    Long-running tasks should call this periodically or on completion to
    ensure fresh permission checks and prevent unbounded cache growth.
    """

    _perm_cache_var.set(None)


@contextmanager
def disable_perm_cache():
    """Context manager to temporarily disable caching of ``has_perm`` calls."""

    token = _cache_disabled_var.set(True)
    try:
        yield
    finally:
        _cache_disabled_var.reset(token)

# --------------------
# MODEL-LEVEL CHECKS
# --------------------

def can_act_on_model(user, model, action):
    if user.is_superuser or user.is_staff:
        return True
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return _cached_has_perm(user, f"{app_label}.{action}_{model_name}")


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

def can_act_on_instance(user, instance, action):
    model = type(instance)
    if user.is_superuser or user.is_staff:
        return True

    checks = {
        "view": (can_view_model, "can_user_view"),
        "change": (can_change_model, "can_user_change"),
        "delete": (can_delete_model, "can_user_delete"),
    }

    if action not in checks:
        raise ValueError(f"Unsupported action: {action}")

    model_check, method_name = checks[action]
    if not model_check(user, model):
        return False
    if hasattr(instance, method_name):
        return getattr(instance, method_name)(user)
    return True


def can_view_instance(user, instance):
    return can_act_on_instance(user, instance, "view")


def can_change_instance(user, instance):
    return can_act_on_instance(user, instance, "change")


def can_delete_instance(user, instance):
    return can_act_on_instance(user, instance, "delete")

# --------------------
# FIELD-LEVEL CHECKS
# --------------------

def _get_perm_codename(model, field_name, action):
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{field_name}"

def can_act_on_field(user, model, field_name, action, instance=None):
    """Return whether ``user`` may perform ``action`` on ``field_name``.

    ``action`` should be ``"view"`` or ``"change"``. When ``instance`` is
    provided, instance-level permissions are also checked.
    """

    if user.is_superuser or user.is_staff:
        return True

    if action == "view":
        if not can_view_model(user, model):
            return False
        if instance and not can_view_instance(user, instance):
            return False
    elif action == "change":
        if not can_change_model(user, model):
            return False
        if instance and not can_change_instance(user, instance):
            return False
    else:
        raise ValueError(f"Unsupported action: {action}")

    return _cached_has_perm(user, _get_perm_codename(model, field_name, action))


def can_read_field(user, model, field_name, instance=None):
    return can_act_on_field(user, model, field_name, "view", instance)


def can_write_field(user, model, field_name, instance=None):
    return can_act_on_field(user, model, field_name, "change", instance)


def _get_fields_by_action(user, model, action, instance=None):
    """Return names of model fields the user may act on for ``action``."""

    fields = [
        field
        for field in list(model._meta.fields) + list(model._meta.many_to_many)
        if not field.auto_created and field.editable
    ]

    if user.is_superuser or user.is_staff:
        return [field.name for field in fields]

    if action == "view":
        if not can_view_model(user, model):
            return []
        if instance and not can_view_instance(user, instance):
            return []
    elif action == "change":
        if not can_change_model(user, model):
            return []
        if instance and not can_change_instance(user, instance):
            return []
    else:
        raise ValueError(f"Unsupported action: {action}")

    return [
        field.name
        for field in fields
        if _cached_has_perm(user, _get_perm_codename(model, field.name, action))
    ]

def get_readable_fields(user, model, instance=None):
    """Return names of model fields the user may read, including M2M fields."""
    return _get_fields_by_action(user, model, "view", instance)


def get_editable_fields(user, model, instance=None):
    """Return names of model fields the user may edit, including M2M fields."""
    return _get_fields_by_action(user, model, "change", instance)

# ----------------------------------------
# INSTANCE-LEVEL QUERYSET FILTER UTILITIES
# ----------------------------------------

def _filter_queryset_by_action(user, queryset: QuerySet, check_func) -> QuerySet:
    """Return ``queryset`` limited to objects where ``check_func`` allows action.

    Objects are streamed using ``queryset.iterator()`` to avoid loading the
    entire queryset at once. The primary keys of permitted objects are
    collected in a list, so very large querysets may consume significant
    memory.
    """

    if user.is_superuser or user.is_staff:
        return queryset

    allowed_ids = [
        obj.pk for obj in queryset.iterator() if check_func(user, obj)
    ]
    return queryset.filter(pk__in=allowed_ids)

def filter_viewable_queryset(user, queryset: QuerySet) -> QuerySet:
    """Return a QuerySet containing only viewable objects for the user.

    If the user lacks view permission on the model, an empty queryset is
    returned. Rows are streamed using ``queryset.iterator()`` instead of
    loading the entire queryset at once. The matching primary keys are still
    collected in a list, so very large querysets may consume significant
    memory.
    """

    model = queryset.model
    if not can_view_model(user, model):
        return queryset.none()
    return _filter_queryset_by_action(user, queryset, can_view_instance)

def filter_editable_queryset(user, queryset: QuerySet) -> QuerySet:
    """Return a QuerySet containing only objects the user may edit.

    If the user lacks change permission on the model, an empty queryset is
    returned. Iterates with ``queryset.iterator()`` to avoid loading all rows
    at once. The list of allowed IDs is still built in memory, which can grow
    large for enormous querysets.
    """

    model = queryset.model
    if not can_change_model(user, model):
        return queryset.none()
    return _filter_queryset_by_action(user, queryset, can_change_instance)

def filter_deletable_queryset(user, queryset: QuerySet) -> QuerySet:
    """Return a QuerySet containing only objects the user may delete.

    If the user lacks delete permission on the model, an empty queryset is
    returned. Uses ``queryset.iterator()`` for streaming evaluation. As with
    the other filters, a list of allowed IDs is accumulated in memory, which
    may be substantial for very large querysets.
    """

    model = queryset.model
    if not can_delete_model(user, model):
        return queryset.none()
    return _filter_queryset_by_action(user, queryset, can_delete_instance)
