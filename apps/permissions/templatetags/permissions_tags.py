from django import template
from apps.permissions.checks import can_read_field, can_write_field

register = template.Library()

@register.simple_tag
def user_can_read(user, model, field_name):
    return can_read_field(user, model, field_name)

@register.simple_tag
def user_can_write(user, model, field_name):
    return can_write_field(user, model, field_name)