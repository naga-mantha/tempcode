from django import template
from apps.permissions.checks import can_read_field, can_write_field

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
