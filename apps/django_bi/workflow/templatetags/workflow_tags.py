from django import template

from apps.django_bi.workflow.apply_transition import get_allowed_transitions
from apps.django_bi.workflow.permissions import (
    can_view_instance_state,
    can_change_instance_state,
    can_delete_instance_state,
    can_read_field_state,
    can_write_field_state,
)

register = template.Library()


def _user_and_obj(context, user_or_obj, obj=None):
    if obj is None:
        if "request" not in context:
            raise ValueError("Template context missing 'request'; pass a user explicitly.")
        user = context["request"].user
        obj = user_or_obj
    else:
        user = user_or_obj
    return user, obj


@register.simple_tag(takes_context=True)
def user_can_view_instance_state(context, user_or_instance, instance=None):
    user, instance = _user_and_obj(context, user_or_instance, instance)
    return can_view_instance_state(user, instance)


@register.simple_tag(takes_context=True)
def user_can_change_instance_state(context, user_or_instance, instance=None):
    user, instance = _user_and_obj(context, user_or_instance, instance)
    return can_change_instance_state(user, instance)


@register.simple_tag(takes_context=True)
def user_can_delete_instance_state(context, user_or_instance, instance=None):
    user, instance = _user_and_obj(context, user_or_instance, instance)
    return can_delete_instance_state(user, instance)


@register.simple_tag(takes_context=True)
def user_can_read_state(context, *args):
    # Accept (user, model, field_name, instance?) or (model, field_name, instance?)
    if args and hasattr(args[0], "is_authenticated"):
        user = args[0]
        model = args[1]
        field_name = args[2]
        instance = args[3] if len(args) > 3 else None
    else:
        if "request" not in context:
            raise ValueError("Template context missing 'request'; pass a user explicitly.")
        user = context["request"].user
        model = args[0]
        field_name = args[1]
        instance = args[2] if len(args) > 2 else None
    return can_read_field_state(user, model, field_name, instance)


@register.simple_tag(takes_context=True)
def user_can_write_state(context, *args):
    if args and hasattr(args[0], "is_authenticated"):
        user = args[0]
        model = args[1]
        field_name = args[2]
        instance = args[3] if len(args) > 3 else None
    else:
        if "request" not in context:
            raise ValueError("Template context missing 'request'; pass a user explicitly.")
        user = context["request"].user
        model = args[0]
        field_name = args[1]
        instance = args[2] if len(args) > 2 else None
    return can_write_field_state(user, model, field_name, instance)


@register.simple_tag(takes_context=True)
def user_can_transition(context, *args):
    """Return whether user may perform transition by name from instance.

    Accepts either (instance, "transition_name") to use request.user, or
    (user, instance, "transition_name").
    """

    if len(args) == 2:
        if "request" not in context:
            raise ValueError("Template context missing 'request'; pass a user explicitly.")
        user = context["request"].user
        instance, name = args
    elif len(args) == 3:
        user, instance, name = args
    else:
        raise ValueError("user_can_transition expects (instance, name) or (user, instance, name)")

    transitions = get_allowed_transitions(instance, user)
    return any(t.name == name for t in transitions)
