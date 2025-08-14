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

_perm_cache_var: ContextVar[dict] = ContextVar("perm_cache", default={})
_cache_disabled_var: ContextVar[bool] = ContextVar("perm_cache_disabled", default=False)


def _cached_has_perm(user, perm: str) -> bool:
    """Return ``user.has_perm(perm)`` using a per-request cache."""

    if _cache_disabled_var.get():
        return user.has_perm(perm)

    cache = _perm_cache_var.get()
    key = (id(user), perm)
    if key not in cache:
        cache[key] = user.has_perm(perm)
    return cache[key]


def clear_perm_cache() -> None:
    """Clear the permission cache.

    Long-running tasks should call this periodically or on completion to
    ensure fresh permission checks and prevent unbounded cache growth.
    """

    _perm_cache_var.set({})


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
    return _cached_has_perm(user, _get_perm_codename(model, field_name, "view"))

def can_write_field(user, model, field_name, instance=None):
    if user.is_superuser or user.is_staff:
        return True
    if not can_change_model(user, model):
        return False
    if instance and not can_change_instance(user, instance):
        return False
    return _cached_has_perm(user, _get_perm_codename(model, field_name, "change"))

def get_readable_fields(user, model, instance=None):
    """Return names of model fields the user may read, including M2M fields."""

    fields = list(model._meta.fields) + list(model._meta.many_to_many)
    return [
        field.name
        for field in fields
        if can_read_field(user, model, field.name, instance)
    ]


def get_editable_fields(user, model, instance=None):
    """Return names of model fields the user may edit, including M2M fields."""

    fields = list(model._meta.fields) + list(model._meta.many_to_many)
    return [
        field.name
        for field in fields
        if can_write_field(user, model, field.name, instance)
    ]

# ----------------------------------------
# INSTANCE-LEVEL QUERYSET FILTER UTILITIES
# ----------------------------------------

def filter_viewable_queryset(user, queryset: QuerySet) -> QuerySet:
    """Return a QuerySet containing only viewable objects for the user."""

    if user.is_superuser or user.is_staff:
        return queryset

    allowed_ids = [obj.pk for obj in queryset if can_view_instance(user, obj)]
    return queryset.filter(pk__in=allowed_ids)

def filter_editable_queryset(user, queryset: QuerySet) -> QuerySet:
    """Return a QuerySet containing only objects the user may edit."""

    if user.is_superuser or user.is_staff:
        return queryset

    allowed_ids = [obj.pk for obj in queryset if can_change_instance(user, obj)]
    return queryset.filter(pk__in=allowed_ids)

def filter_deletable_queryset(user, queryset: QuerySet) -> QuerySet:
    """Return a QuerySet containing only objects the user may delete."""

    if user.is_superuser or user.is_staff:
        return queryset

    allowed_ids = [obj.pk for obj in queryset if can_delete_instance(user, obj)]
    return queryset.filter(pk__in=allowed_ids)
