from typing import Dict, Any, Callable, List, Tuple, Optional
from apps.common.models.planning import BaseMrpMessage
from .business_partners import supplier_choices
from .items import item_choices
from .po_categories import po_category_choices
from .item_groups import item_group_choices
from .item_group_types import item_group_type_choices
from .programs import program_choices
from .item_types import item_type_choices

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


def _default_label(field_path: str, fallback: str = "") -> str:
    try:
        tail = (field_path or "").split("__")[-1]
        return (tail or fallback or "").replace("_", " ").title()
    except Exception:
        return fallback or ""


def text_filter(field_path: str, *, label: Optional[str] = None, lookup: str = "icontains") -> Dict[str, Any]:
    """Generic text filter for a given model field path.

    Defaults to case-insensitive contains. V2 QueryBuilder supplies sensible defaults
    for type='text', but you may pass an explicit lookup via overrides when needed.
    """
    cfg: Dict[str, Any] = {
        "label": label or _default_label(field_path, "Text"),
        "type": "text",
        "field": field_path,
    }
    # Optional lookup hint for custom resolvers
    if lookup:
        cfg["lookup"] = lookup
    return cfg


def multiselect_filter(
    field_path: str,
    *,
    label: Optional[str] = None,
    choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None,
    maxItems: int = 100000,
    handler: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Generic multiselect filter for a given field path + choices callable.

    - choices_func should be a callable(user, query, ids=None) -> List[Tuple[value,label]]
    - If no handler is provided, a default __in filter is used server-side.
    """
    def _default_handler(qs, val):
        return qs.filter(**{f"{field_path}__in": val}) if val else qs

    return {
        "label": label or _default_label(field_path, "Values"),
        "type": "multiselect",
        "multiple": True,
        "choices": choices_func or [],
        "field": field_path,
        "tom_select_options": {
            "placeholder": f"Select {label or _default_label(field_path)}...",
            "plugins": ["remove_button"],
            "maxItems": maxItems,
        },
        "handler": handler or _default_handler,
    }


def supplier_filter(supplier_code_path: str, maxItems: int = 100000, label: str = "Supplier", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        supplier_code_path,
        label=label,
        choices_func=choices_func or supplier_choices,
        maxItems=maxItems,
    )


def item_filter(item_code_path: str, maxItems: int = 100000, label: str = "Item", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        item_code_path,
        label=label,
        choices_func=choices_func or item_choices,
        maxItems=maxItems,
    )


def item_group_filter(item_group_code_path: str, maxItems: int = 100000, label: str = "Item Group", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        item_group_code_path,
        label=label,
        choices_func=choices_func or item_group_choices,
        maxItems=maxItems,
    )


def item_group_type_filter(item_group_type_code_path: str, maxItems: int = 100000, label: str = "Item Group Type", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        item_group_type_code_path,
        label=label,
        choices_func=choices_func or item_group_type_choices,
        maxItems=maxItems,
    )


def program_filter(program_code_path: str, maxItems: int = 100000, label: str = "Program", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        program_code_path,
        label=label,
        choices_func=choices_func or program_choices,
        maxItems=maxItems,
    )


def item_type_filter(item_type_code_path: str, maxItems: int = 100000, label: str = "Item Type", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        item_type_code_path,
        label=label,
        choices_func=choices_func or item_type_choices,
        maxItems=maxItems,
    )


def mrp_reschedule_direction_filter(direction_path: str, maxItems: int = 100000, label: str = "Reschedule Direction") -> Dict[str, Any]:
    cfg = multiselect_filter(direction_path, label=label, maxItems=maxItems)
    # Static choices list; V2 will render these without AJAX
    cfg["choices"] = list(BaseMrpMessage.DIRECTION_CHOICES)
    return cfg


def purchase_order_category_filter(po_category_code_path: str, maxItems: int = 100000, label: str = "PO Category", choices_func: Optional[Callable[[Any, str], List[Tuple[str, str]]]] = None) -> Dict[str, Any]:
    return multiselect_filter(
        po_category_code_path,
        label=label,
        choices_func=choices_func or po_category_choices,
        maxItems=maxItems,
    )


__all__ = [
    # Generic helpers
    "text_filter",
    "multiselect_filter",
    "date_from_filter",
    "date_to_filter",
    # Compatibility shims (prefer generic helpers in new code)
    "supplier_filter",
    "item_filter",
    "item_group_filter",
    "item_group_type_filter",
    "program_filter",
    "item_type_filter",
    "mrp_reschedule_direction_filter",
    "purchase_order_category_filter",
]
