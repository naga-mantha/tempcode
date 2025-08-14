from django import template
from apps.permissions.checks import (
    can_add_model,
    can_change_instance,
    can_change_model,
    can_delete_instance,
    can_delete_model,
    can_read_field,
    can_view_instance,
    can_view_model,
    can_write_field,
)

register = template.Library()


@register.simple_tag
def user_can_read(user, model, field_name, instance=None):
    """Return whether ``user`` may read ``field_name`` on ``model``.

    An optional ``instance`` can be supplied to include instance-level
    permission checks.
    """

    return can_read_field(user, model, field_name, instance)


@register.simple_tag
def user_can_write(user, model, field_name, instance=None):
    """Return whether ``user`` may edit ``field_name`` on ``model``.

    When an ``instance`` is provided, instance-level permissions are honored.
    """

    return can_write_field(user, model, field_name, instance)


@register.simple_tag
def user_can_view_model(user, model):
    """Return whether ``user`` may view ``model``."""

    return can_view_model(user, model)


@register.simple_tag
def user_can_add_model(user, model):
    """Return whether ``user`` may add ``model`` instances."""

    return can_add_model(user, model)


@register.simple_tag
def user_can_change_model(user, model):
    """Return whether ``user`` may change ``model`` instances."""

    return can_change_model(user, model)


@register.simple_tag
def user_can_delete_model(user, model):
    """Return whether ``user`` may delete ``model`` instances."""

    return can_delete_model(user, model)


@register.simple_tag
def user_can_view_instance(user, instance):
    """Return whether ``user`` may view ``instance``."""

    return can_view_instance(user, instance)


@register.simple_tag
def user_can_change_instance(user, instance):
    """Return whether ``user`` may change ``instance``."""

    return can_change_instance(user, instance)


@register.simple_tag
def user_can_delete_instance(user, instance):
    """Return whether ``user`` may delete ``instance``."""

    return can_delete_instance(user, instance)
