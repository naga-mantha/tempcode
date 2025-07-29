from django import template
from apps.workflow.views.permissions import get_field_permission

register = template.Library()

@register.inclusion_tag("components/form_group.html", takes_context=True)
def render_field(context, field, layout="vertical"):
    # user = context['request'].user
    # model = getattr(field.form._meta, 'model', None)
    # field_name = field.name

    # Default to editable
    perm = "write"
    # if model:
    #     perm = get_field_permission(user=user, model=model, field_name=field_name)
    return {
        "field": field,
        "readonly": perm == "read",
        "hidden": perm == "hide",
        "layout": layout,
    }