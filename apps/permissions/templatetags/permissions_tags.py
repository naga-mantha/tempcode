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


def _user_and_obj(context, user_or_obj, obj=None):
    """Return a ``(user, obj)`` tuple.

    When ``obj`` is ``None`` the first positional argument is treated as
    ``obj`` and ``context['request'].user`` is used for the user. The template
    context must include ``request`` when the user argument is omitted.
    """

    if obj is None:
        if "request" not in context:
            raise ValueError(
                "Template context does not include 'request'; pass a user "
                "explicitly."
            )
        user = context["request"].user
        obj = user_or_obj
    else:
        user = user_or_obj
    return user, obj


def _user_model_field_instance(context, *args):
    """Return ``(user, model, field_name, instance)`` from ``args``.

    The ``user`` argument is optional; when omitted the current request user is
    used. The ``instance`` argument remains optional. The template context must
    include ``request`` when the user argument is omitted.
    """

    if args and hasattr(args[0], "is_authenticated"):
        user = args[0]
        model = args[1]
        field_name = args[2]
        instance = args[3] if len(args) > 3 else None
    else:
        if "request" not in context:
            raise ValueError(
                "Template context does not include 'request'; pass a user "
                "explicitly."
            )
        user = context["request"].user
        model = args[0]
        field_name = args[1]
        instance = args[2] if len(args) > 2 else None
    return user, model, field_name, instance


@register.simple_tag(takes_context=True)
def user_can_read(context, *args):
    """Return whether ``user`` may read ``field_name`` on ``model``.

    An optional ``instance`` can be supplied to include instance-level
    permission checks. When ``user`` is omitted, ``context['request'].user`` is
    used.
    """

    user, model, field_name, instance = _user_model_field_instance(context, *args)
    return can_read_field(user, model, field_name, instance)


@register.simple_tag(takes_context=True)
def user_can_write(context, *args):
    """Return whether ``user`` may edit ``field_name`` on ``model``.

    When an ``instance`` is provided, instance-level permissions are honored.
    When ``user`` is omitted, ``context['request'].user`` is used.
    """

    user, model, field_name, instance = _user_model_field_instance(context, *args)
    return can_write_field(user, model, field_name, instance)


@register.simple_tag(takes_context=True)
def user_can_view_model(context, user_or_model, model=None):
    """Return whether ``user`` may view ``model``.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, model = _user_and_obj(context, user_or_model, model)
    return can_view_model(user, model)


@register.simple_tag(takes_context=True)
def user_can_add_model(context, user_or_model, model=None):
    """Return whether ``user`` may add ``model`` instances.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, model = _user_and_obj(context, user_or_model, model)
    return can_add_model(user, model)


@register.simple_tag(takes_context=True)
def user_can_change_model(context, user_or_model, model=None):
    """Return whether ``user`` may change ``model`` instances.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, model = _user_and_obj(context, user_or_model, model)
    return can_change_model(user, model)


@register.simple_tag(takes_context=True)
def user_can_delete_model(context, user_or_model, model=None):
    """Return whether ``user`` may delete ``model`` instances.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, model = _user_and_obj(context, user_or_model, model)
    return can_delete_model(user, model)


@register.simple_tag(takes_context=True)
def user_can_view_instance(context, user_or_instance, instance=None):
    """Return whether ``user`` may view ``instance``.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, instance = _user_and_obj(context, user_or_instance, instance)
    return can_view_instance(user, instance)


@register.simple_tag(takes_context=True)
def user_can_change_instance(context, user_or_instance, instance=None):
    """Return whether ``user`` may change ``instance``.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, instance = _user_and_obj(context, user_or_instance, instance)
    return can_change_instance(user, instance)


@register.simple_tag(takes_context=True)
def user_can_delete_instance(context, user_or_instance, instance=None):
    """Return whether ``user`` may delete ``instance``.

    ``user`` can be omitted to default to ``context['request'].user``.
    """

    user, instance = _user_and_obj(context, user_or_instance, instance)
    return can_delete_instance(user, instance)
