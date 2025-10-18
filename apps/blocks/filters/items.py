"""Choice helpers for Item-related filters bundled with Blocks."""
from __future__ import annotations

from typing import List, Optional, Tuple

from django.db.models import Q

from apps.blocks.models.item import Item


def _apply_search(qs, query: str):
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
    return qs


def _format_choices(qs, limit: int = 200) -> List[Tuple[str, str]]:
    return [
        (obj.code, f"{obj.code} - {obj.description}".strip())
        for obj in qs.order_by("code")[:limit]
    ]


def item_choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Return ``Item`` choices as ``(code, "code - description")`` tuples."""

    qs = Item.objects.all()
    if ids:
        qs = qs.filter(code__in=ids)
    qs = _apply_search(qs, query)
    return _format_choices(qs)


__all__ = ["item_choices"]
