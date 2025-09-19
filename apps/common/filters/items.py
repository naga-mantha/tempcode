from typing import List, Tuple, Callable, Optional

from apps.common.models import Item
from django.db.models import Q


def _apply_item_search(qs, query: str):
    """Apply case-insensitive search on code/description if query provided."""
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
    return qs


def format_item_choices(qs, limit: int = 200) -> List[Tuple[str, str]]:
    """Format a queryset of Items into (value, label) pairs with a limit."""
    return [
        (i.code, f"{i.code} - {i.description}".strip())
        for i in qs.order_by("code")[:limit]
    ]

def make_item_choices_for_queryset(qs_provider: Callable[[object], "models.QuerySet[Item]"]):
    """Factory: build an item choices function based on a base queryset provider.

    qs_provider(user) -> QuerySet[Item]
    Returned function conforms to (user, query) signature used by FilterChoicesView.
    """
    def _choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        qs = qs_provider(user)
        if ids:
            qs = qs.filter(code__in=ids)
        qs = _apply_item_search(qs, query)
        return format_item_choices(qs)

    return _choices

def item_choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Return item choices as (code, "code - description")."""
    qs = Item.objects.all()
    if ids:
        qs = qs.filter(code__in=ids)
    qs = _apply_item_search(qs, query)
    return format_item_choices(qs)

# START ADDING FROM HERE
def item_choices_for_open_po(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Return item choices limited to Items that appear on open PurchaseOrderLines."""
    base = Item.objects.filter(purchaseorderline__status="open").distinct()
    if ids:
        base = base.filter(code__in=ids)
    qs = _apply_item_search(base, query)
    return format_item_choices(qs)

__all__ = [
    "make_item_choices_for_queryset",
    "item_choices",
    "item_choices_for_open_po",
]
