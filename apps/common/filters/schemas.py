from typing import Dict, Any

from django.urls import reverse
from django.db.models import Q

from .business_partners import supplier_choices
from .items import item_choices


def supplier_filter(block_name: str, supplier_id_path: str, label: str = "Supplier") -> Dict[str, Any]:
    """Reusable supplier selector filter.

    supplier_id_path: Django lookup path to supplier id (e.g., "po_line__order__supplier_id").
    """

    def handler(qs, val):
        if not val:
            return qs
        try:
            supplier_id = int(val)
        except Exception:
            return qs
        return qs.filter(**{supplier_id_path: supplier_id})

    return {
        "label": label,
        "type": "select",
        "choices": supplier_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "supplier"]),
        "handler": handler,
    }


def item_multiselect_filter(block_name: str, item_code_path: str, label: str = "Item") -> Dict[str, Any]:
    """Reusable item multi-select filter.

    item_code_path: Django lookup path to item code (e.g., "item__code").
    """

    def handler(qs, val):
        return qs.filter(**{f"{item_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": item_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "item"]),
        "tom_select_options": {
            "placeholder": "Search items...",
            "plugins": ["remove_button"],
            "maxItems": 3,
        },
        "handler": handler,
    }


def item_multiselect_filter_any(block_name: str, item_code_paths: list[str], label: str = "Item") -> Dict[str, Any]:
    """Item multi-select filter that matches any of the provided code paths.

    Example: ["pol__item__code", "production_order__item__code"]
    """

    def handler(qs, val):
        if not val:
            return qs
        cond = Q()
        for path in item_code_paths:
            cond |= Q(**{f"{path}__in": val})
        return qs.filter(cond)

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": item_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "item"]),
        "tom_select_options": {
            "placeholder": "Search items...",
            "plugins": ["remove_button"],
            "maxItems": 3,
        },
        "handler": handler,
    }


def date_from_filter(key: str, label: str, date_field_path: str) -> Dict[str, Any]:
    """Generic from-date filter for a given date/datetime field path."""

    lookup = f"{date_field_path}__gte"

    def handler(qs, val):
        return qs.filter(**{lookup: val}) if val else qs

    return {
        "label": label,
        "type": "date",
        "handler": handler,
    }


def date_to_filter(key: str, label: str, date_field_path: str) -> Dict[str, Any]:
    """Generic to-date filter for a given date/datetime field path."""

    lookup = f"{date_field_path}__lte"

    def handler(qs, val):
        return qs.filter(**{lookup: val}) if val else qs

    return {
        "label": label,
        "type": "date",
        "handler": handler,
    }


__all__ = [
    "supplier_filter",
    "item_multiselect_filter",
    "item_multiselect_filter_any",
    "date_from_filter",
    "date_to_filter",
]
