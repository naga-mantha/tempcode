"""Choice helpers for ``ItemGroup`` records bundled with Blocks."""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from django.db import models
from django.db.models import Q

from apps.blocks.models.item_group import ItemGroup


ChoiceCallable = Callable[[object, str, Optional[List[str]]], List[Tuple[str, str]]]


def _apply_search(qs, query: str):
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
    return qs


def _format_choices(qs, limit: int = 200) -> List[Tuple[str, str]]:
    return [
        (obj.code, f"{obj.code} - {obj.description}".strip())
        for obj in qs.order_by("code")[:limit]
    ]


def make_item_group_choices_for_queryset(qs_provider: Callable[[object], "models.QuerySet[ItemGroup]"]):
    """Factory that turns a queryset provider into a filter choices callable."""

    def _choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        qs = qs_provider(user)
        if ids:
            qs = qs.filter(code__in=ids)
        qs = _apply_search(qs, query)
        return _format_choices(qs)

    return _choices


def item_group_choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    qs = ItemGroup.objects.all()
    if ids:
        qs = qs.filter(code__in=ids)
    qs = _apply_search(qs, query)
    return _format_choices(qs)


__all__ = [
    "ChoiceCallable",
    "make_item_group_choices_for_queryset",
    "item_group_choices",
]
