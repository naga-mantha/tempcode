from typing import Dict, Any, Callable, List, Tuple, Optional

from django.urls import reverse
from django.db.models import Q

from .business_partners import supplier_choices
from .items import item_choices
from .po_categories import po_category_choices
from .item_groups import item_group_choices
from .item_group_types import item_group_type_choices
from .programs import program_choices
from .item_types import item_type_choices

def supplier_filter(
    block_name: str,
    supplier_code_path: str,
    maxItems: int = 100000,
    label: str = "Supplier",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable supplier selector filter.

    supplier_code_path: Django lookup path to supplier code (e.g., "order__supplier__code").
    """

    def handler(qs, val):
        return qs.filter(**{f"{supplier_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or supplier_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "supplier"]),
        # value_path is used to compute allowed values from the filtered queryset
        # for interdependent narrowing of options.
        "value_path": supplier_code_path,
        "tom_select_options": {
            "placeholder": "Search suppliers...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler,
    }


def item_filter(
    block_name: str,
    item_code_path: str,
    maxItems: int = 100000,
    label: str = "Item",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable item multi-select filter.

    item_code_path: Django lookup path to item code (e.g., "item__code").
    """

    def handler(qs, val):
        return qs.filter(**{f"{item_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or item_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "item"]),
        "value_path": item_code_path,
        "tom_select_options": {
            "placeholder": "Search items...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler,
    }

def item_group_filter(
    block_name: str,
    item_group_code_path: str,
    maxItems: int = 100000,
    label: str = "Item Group",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable item group multi-select filter.

    item_group_code_path: Django lookup path to item code (e.g., "item_group__code").
    """

    def handler(qs, val):
        return qs.filter(**{f"{item_group_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or item_group_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "item_group"]),
        "value_path": item_group_code_path,
        "tom_select_options": {
            "placeholder": "Search item groups...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler,
    }

def item_group_type_filter(
    block_name: str,
    item_group_type_code_path: str,
    maxItems: int = 100000,
    label: str = "Item Group Type",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable item group type multi-select filter."""

    def handler(qs, val):
        return qs.filter(**{f"{item_group_type_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or item_group_type_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "item_group_type"]),
        "value_path": item_group_type_code_path,
        "tom_select_options": {
            "placeholder": "Search item group types...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler,
    }

def program_filter(
    block_name: str,
    program_code_path: str,
    maxItems: int = 100000,
    label: str = "Program",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable program multi-select filter."""

    def handler(qs, val):
        return qs.filter(**{f"{program_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or program_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "program"]),
        "value_path": program_code_path,
        "tom_select_options": {
            "placeholder": "Search programs...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler,
    }

def item_type_filter(
    block_name: str,
    item_type_code_path: str,
    maxItems: int = 100000,
    label: str = "Item Type",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable item type multi-select filter."""

    def handler(qs, val):
        return qs.filter(**{f"{item_type_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or item_type_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "item_type"]),
        "value_path": item_type_code_path,
        "tom_select_options": {
            "placeholder": "Search item types...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler,
    }

def purchase_order_category_filter(
    block_name: str,
    po_category_code_path: str,
    maxItems: int = 100000,
    label: str = "PO Category",
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """Reusable item multi-select filter.

    item_code_path: Django lookup path to item code (e.g., "item__code").
    """

    def handler(qs, val):
        return qs.filter(**{f"{po_category_code_path}__in": val}) if val else qs

    return {
        "label": label,
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or po_category_choices,
        "choices_url": reverse("block_filter_choices", args=[block_name, "category"]),
        "value_path": po_category_code_path,
        "tom_select_options": {
            "placeholder": "Search categories...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
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
    "item_filter",
    "item_group_filter",
    "item_group_type_filter",
    "program_filter",
    "item_type_filter",
    "purchase_order_category_filter",
    "date_from_filter",
    "date_to_filter",
]
