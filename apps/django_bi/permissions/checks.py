# apps/django_bi/permissions/checks.py

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

from django.conf import settings
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


def has_perm_cached(user, perm: str) -> bool:
    """Public wrapper to check a permission using the per-request cache.

    Falls back to ``user.has_perm`` when caching is disabled.
    """

    return _cached_has_perm(user, perm)


def _bypass_all(user) -> bool:
    """Return True if the user should bypass all permission checks.

    Superusers always bypass. Staff bypass is controlled by the
    ``PERMISSIONS_STAFF_BYPASS`` setting (defaults to True for backwards
    compatibility).
    """

    if getattr(user, "is_superuser", False):
        return True
    staff_bypass = getattr(settings, "PERMISSIONS_STAFF_BYPASS", True)
    return staff_bypass and getattr(user, "is_staff", False)


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
    """Return whether ``user`` may perform ``action`` on ``model``.

    Args:
        user: The user being checked.
        model: The Django model class to inspect.
        action: Permission prefix such as ``"view"`` or ``"change"``.

    Returns:
        bool: ``True`` if the user has the requested model-level permission.
    """

    if _bypass_all(user):
        return True
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return _cached_has_perm(user, f"{app_label}.{action}_{model_name}")


def can_view_model(user, model):
    """Return whether ``user`` may view instances of ``model``.

    Args:
        user: The user being checked.
        model: The Django model class to inspect.

    Returns:
        bool: ``True`` if the user can view the model.
    """

    return can_act_on_model(user, model, "view")


def can_add_model(user, model):
    """Return whether ``user`` may add instances of ``model``.

    Args:
        user: The user being checked.
        model: The Django model class to inspect.

    Returns:
        bool: ``True`` if the user can add the model.
    """

    return can_act_on_model(user, model, "add")


def can_change_model(user, model):
    """Return whether ``user`` may change instances of ``model``.

    Args:
        user: The user being checked.
        model: The Django model class to inspect.

    Returns:
        bool: ``True`` if the user can change the model.
    """

    return can_act_on_model(user, model, "change")


def can_delete_model(user, model):
    """Return whether ``user`` may delete instances of ``model``.

    Args:
        user: The user being checked.
        model: The Django model class to inspect.

    Returns:
        bool: ``True`` if the user can delete the model.
    """

    return can_act_on_model(user, model, "delete")

# ------------------------
# INSTANCE-LEVEL CHECKS
# ------------------------

# Mapping of instance-level actions to their model check functions and
# optional instance method names.
_INSTANCE_ACTIONS = {
    "view": (can_view_model, "can_user_view"),
    "change": (can_change_model, "can_user_change"),
    "delete": (can_delete_model, "can_user_delete"),
}

def can_act_on_instance(user, instance, action):
    """Return whether ``user`` may perform ``action`` on ``instance``.

    Args:
        user: The user being checked.
        instance: The model instance to inspect.
        action: Permission prefix such as ``"view"`` or ``"delete"``.

    Returns:
        bool: ``True`` if the user has the requested instance-level permission.
    """

    model = type(instance)
    if _bypass_all(user):
        return True

    if action not in _INSTANCE_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")

    model_check, method_name = _INSTANCE_ACTIONS[action]
    if not model_check(user, model):
        return False
    if hasattr(instance, method_name):
        return getattr(instance, method_name)(user)
    return True


def can_view_instance(user, instance):
    """Return whether ``user`` may view ``instance``.

    Args:
        user: The user being checked.
        instance: The model instance to inspect.

    Returns:
        bool: ``True`` if the user can view the instance.
    """

    return can_act_on_instance(user, instance, "view")


def can_change_instance(user, instance):
    """Return whether ``user`` may change ``instance``.

    Args:
        user: The user being checked.
        instance: The model instance to inspect.

    Returns:
        bool: ``True`` if the user can change the instance.
    """

    return can_act_on_instance(user, instance, "change")


def can_delete_instance(user, instance):
    """Return whether ``user`` may delete ``instance``.

    Args:
        user: The user being checked.
        instance: The model instance to inspect.

    Returns:
        bool: ``True`` if the user can delete the instance.
    """

    return can_act_on_instance(user, instance, "delete")

# --------------------
# FIELD-LEVEL CHECKS
# --------------------

def _get_full_permission_name(model, field_name, action):
    """Return the full permission name for acting on a model field.

    Args:
        model: The Django model class containing the field.
        field_name: Name of the field being checked.
        action: Permission prefix such as ``"view"`` or ``"change"``.

    Returns:
        str: Permission name in ``"app_label.codename"`` format for the field
            action.
    """

    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{action}_{model_name}_{field_name}"

def can_act_on_field(user, model, field_name, action, instance=None):
    """Return whether ``user`` may perform ``action`` on ``field_name``.

    ``action`` should be ``"view"`` or ``"change"``. When ``instance`` is
    provided, instance-level permissions are also checked.
    """

    if _bypass_all(user):
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

    return _cached_has_perm(user, _get_full_permission_name(model, field_name, action))


def can_read_field(user, model, field_name, instance=None):
    """Return whether ``user`` may view ``field_name`` on ``model``.

    Args:
        user: The user being checked.
        model: The Django model class containing the field.
        field_name: Name of the field being inspected.
        instance: Optional model instance for instance-level checks.

    Returns:
        bool: ``True`` if the field may be viewed.
    """

    return can_act_on_field(user, model, field_name, "view", instance)


def can_write_field(user, model, field_name, instance=None):
    """Return whether ``user`` may change ``field_name`` on ``model``.

    Args:
        user: The user being checked.
        model: The Django model class containing the field.
        field_name: Name of the field being inspected.
        instance: Optional model instance for instance-level checks.

    Returns:
        bool: ``True`` if the field may be modified.
    """

    return can_act_on_field(user, model, field_name, "change", instance)


def _get_fields_by_action(user, model, action, instance=None):
    """Return names of model fields the user may act on for ``action``."""

    fields = [
        field
        for field in list(model._meta.fields) + list(model._meta.many_to_many)
        if not field.auto_created and field.editable
    ]

    if _bypass_all(user):
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
        if _cached_has_perm(user, _get_full_permission_name(model, field.name, action))
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

def _filter_queryset_by_action(
    user, queryset: QuerySet, check_func, *, chunk_size: int = 2000
) -> QuerySet:
    """Return ``queryset`` limited to objects where ``check_func`` allows action.

    Objects are streamed using ``queryset.iterator(chunk_size=...)`` and the
    matching primary keys are processed in smaller batches. Each batch is
    filtered with ``pk__in`` to avoid building a single large list of IDs in
    memory.
    """

    if _bypass_all(user):
        return queryset

    allowed_qs = queryset.none()
    batch: list[int] = []
    for obj in queryset.iterator(chunk_size=chunk_size):
        if check_func(user, obj):
            batch.append(obj.pk)
        if len(batch) >= chunk_size:
            allowed_qs |= queryset.filter(pk__in=batch)
            batch.clear()
    if batch:
        allowed_qs |= queryset.filter(pk__in=batch)
    return allowed_qs

def filter_viewable_queryset(user, queryset: QuerySet, *, chunk_size: int = 2000) -> QuerySet:
    """Return a QuerySet containing only viewable objects for the user.

    If the user lacks view permission on the model, an empty queryset is
    returned. Rows are streamed using ``queryset.iterator()`` and processed in
    batches, so only small groups of primary keys are kept in memory at a time.
    """

    model = queryset.model
    if not can_view_model(user, model):
        return queryset.none()
    return _filter_queryset_by_action(user, queryset, can_view_instance, chunk_size=chunk_size)

def filter_editable_queryset(user, queryset: QuerySet, *, chunk_size: int = 2000) -> QuerySet:
    """Return a QuerySet containing only objects the user may edit.

    If the user lacks change permission on the model, an empty queryset is
    returned. The queryset is streamed with ``queryset.iterator()`` and
    evaluated in batches to avoid accumulating all matching IDs in memory.
    """

    model = queryset.model
    if not can_change_model(user, model):
        return queryset.none()
    return _filter_queryset_by_action(user, queryset, can_change_instance, chunk_size=chunk_size)

def filter_deletable_queryset(user, queryset: QuerySet, *, chunk_size: int = 2000) -> QuerySet:
    """Return a QuerySet containing only objects the user may delete.

    If the user lacks delete permission on the model, an empty queryset is
    returned. The queryset is streamed using ``queryset.iterator()`` and
    evaluated in batches so only a limited number of primary keys are stored at
    once.
    """

    model = queryset.model
    if not can_delete_model(user, model):
        return queryset.none()
    return _filter_queryset_by_action(user, queryset, can_delete_instance, chunk_size=chunk_size)

# ----------------------------
# ACTION → CHECK MAP EXPORTS
# ----------------------------

def get_model_check(action: str):
    """Return the model-level check function for the given action.

    Supported actions: "view", "add", "change", "delete".
    """

    mapping = {
        "view": can_view_model,
        "add": can_add_model,
        "change": can_change_model,
        "delete": can_delete_model,
    }
    try:
        return mapping[action]
    except KeyError:
        raise ValueError(f"Unknown permission action: {action}")


def get_instance_check(action: str):
    """Return the instance-level check function for the given action.

    Supported actions: "view", "change", "delete".
    """

    mapping = {
        "view": can_view_instance,
        "change": can_change_instance,
        "delete": can_delete_instance,
    }
    try:
        return mapping[action]
    except KeyError:
        raise ValueError(f"Unknown permission action: {action}")
