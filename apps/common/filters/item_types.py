from typing import List, Tuple, Callable, Optional

from apps.common.models import ItemType
from django.db.models import Q


def _apply_item_type_search(qs, query: str):
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
    return qs


def format_item_type_choices(qs, limit: int = 200) -> List[Tuple[str, str]]:
    return [
        (o.code, f"{o.code} - {o.description}".strip(" -"))
        for o in qs.order_by("code")[:limit]
    ]


def make_item_type_choices_for_queryset(qs_provider: Callable[[object], "models.QuerySet[ItemType]"]):
    def _choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        qs = qs_provider(user)
        if ids:
            qs = qs.filter(code__in=ids)
        qs = _apply_item_type_search(qs, query)
        return format_item_type_choices(qs)

    return _choices


def item_type_choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    qs = ItemType.objects.all()
    if ids:
        qs = qs.filter(code__in=ids)
    qs = _apply_item_type_search(qs, query)
    return format_item_type_choices(qs)


def item_type_choices_for_open_po(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    # ItemType <- Item (type) <- PurchaseOrderLine (item)
    base = ItemType.objects.filter(item__purchaseorderline__status="open").distinct()
    if ids:
        base = base.filter(code__in=ids)
    qs = _apply_item_type_search(base, query)
    return format_item_type_choices(qs)


__all__ = [
    "make_item_type_choices_for_queryset",
    "item_type_choices",
    "item_type_choices_for_open_po",
]

