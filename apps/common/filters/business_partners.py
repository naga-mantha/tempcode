from typing import List, Tuple

from apps.common.models import BusinessPartner
from django.db.models import Q


def supplier_choices(user, query: str = "") -> List[Tuple[int, str]]:
    """Return supplier choices as (id, "code - name")."""
    qs = BusinessPartner.objects.all()
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
    return [(bp.id, f"{bp.code} - {bp.name}".strip(" -")) for bp in qs.order_by("code")[:50]]


__all__ = [
    "supplier_choices",
]

