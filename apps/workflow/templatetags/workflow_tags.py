# NOT NEEDED ANYMORE



from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag("workflow/_transition_form.html", takes_context=True)
def render_transition_form(context, obj, url_name):
    """
    Renders the transition form for any workflow-enabled object.
    Usage: {% render_transition_form employee 'frms:apply_transition' %}
    """
    user = context["request"].user
    transitions = obj.get_available_transitions(user)
    action_url = reverse(url_name, args=[obj.pk])

    return {
        "transitions": transitions,
        "action_url": action_url,
    }
