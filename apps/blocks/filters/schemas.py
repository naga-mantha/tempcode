"""Schema helpers for building filter definitions used by V2 services."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


def _default_label(field_path: str, fallback: str = "") -> str:
    tail = (field_path or "").split("__")[-1]
    tail = tail or fallback or ""
    return tail.replace("_", " ").title()


def text_filter(field_path: str, *, label: Optional[str] = None, lookup: str = "icontains") -> Dict[str, Any]:
    """Return a simple text filter definition for the given field path."""

    cfg: Dict[str, Any] = {
        "label": label or _default_label(field_path, "Text"),
        "type": "text",
        "field": field_path,
    }
    if lookup:
        cfg["lookup"] = lookup
    return cfg


def multiselect_filter(
    field_path: str,
    *,
    label: Optional[str] = None,
    choices_func: Optional[Callable[[Any, str, Optional[List[str]]], List[Tuple[str, str]]]] = None,
    maxItems: int = 100_000,
    handler: Optional[Callable[[Any, Any], Any]] = None,
) -> Dict[str, Any]:
    """Return a multiselect filter definition with optional server-side handler."""

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


__all__ = ["text_filter", "multiselect_filter"]
