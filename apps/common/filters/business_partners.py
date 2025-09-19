from typing import List, Tuple, Callable

from apps.common.models import BusinessPartner
from django.db.models import Q


def _apply_supplier_search(qs, query: str):
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
    return qs

def format_supplier_choices(qs, limit: int = 50) -> List[Tuple[str, str]]:
    return [
        (bp.code, f"{bp.code} - {bp.name}".strip(" -"))
        for bp in qs.order_by("code")[:limit]
    ]

def make_supplier_choices_for_queryset(qs_provider: Callable[[object], "models.QuerySet[BusinessPartner]"]):
    def _choices(user, query: str = "") -> List[Tuple[str, str]]:
        qs = _apply_supplier_search(qs_provider(user), query)
        return format_supplier_choices(qs)
    return _choices

# START ADDING FROM HERE
def supplier_choices(user, query: str = "") -> List[Tuple[str, str]]:
    """Return supplier choices as (code, "code - name")."""
    qs = _apply_supplier_search(BusinessPartner.objects.all(), query)
    return format_supplier_choices(qs)

def supplier_choices_for_open_po(user, query: str = "") -> List[Tuple[str, str]]:
    """Suppliers that appear on open Purchase Order Lines."""
    base = BusinessPartner.objects.filter(purchaseorder__purchaseorderline__status="open").distinct()
    qs = _apply_supplier_search(base, query)
    return format_supplier_choices(qs)


__all__ = [
    "make_supplier_choices_for_queryset",
    "supplier_choices",
    "supplier_choices_for_open_po",
]
