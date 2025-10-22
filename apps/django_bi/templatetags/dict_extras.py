"""Template filters shared across Django BI layouts and blocks."""
from __future__ import annotations

import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(d, key):
    """Safely look up ``key`` on a mapping-like object ``d``."""
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
