from django import template
import json
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def tojson(value):
    """Serialize a Python object to JSON for embedding in templates."""
    try:
        return mark_safe(json.dumps(value))
    except Exception:
        return mark_safe("null")
