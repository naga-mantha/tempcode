from typing import List, Tuple, Callable

from apps.common.models import PurchaseOrderCategory
from django.db.models import Q


def _apply_po_category_search(qs, query: str):
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
    return qs

def format_po_category_choices(qs, limit: int = 50) -> List[Tuple[str, str]]:
    return [
        (cat.code, f"{cat.code} - {cat.description}".strip(" -"))
        for cat in qs.order_by("code")[:limit]
    ]

def make_po_category_choices_for_queryset(qs_provider: Callable[[object], "models.QuerySet[PurchaseOrderCategory]"]):
    def _choices(user, query: str = "") -> List[Tuple[str, str]]:
        qs = _apply_po_category_search(qs_provider(user), query)
        return format_po_category_choices(qs)
    return _choices

# START ADDING FROM HERE
def po_category_choices(user, query: str = "") -> List[Tuple[str, str]]:
    """Return PO category choices as (code, "code - description")."""
    qs = _apply_po_category_search(PurchaseOrderCategory.objects.all(), query)
    return format_po_category_choices(qs)

def po_category_choices_for_open_po(user, query: str = "") -> List[Tuple[str, str]]:
    """Suppliers that appear on open Purchase Order Lines."""
    base = PurchaseOrderCategory.objects.filter(purchaseorder__purchaseorderline__status="open").distinct()
    qs = _apply_po_category_search(base, query)
    return format_po_category_choices(qs)


__all__ = [
    "make_po_category_choices_for_queryset",
    "po_category_choices",
    "po_category_choices_for_open_po"
]
