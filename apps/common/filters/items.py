from typing import List, Tuple

from apps.common.models import Item
from django.db.models import Q


def item_choices(user, query: str = "") -> List[Tuple[str, str]]:
    """Return item choices as (code, "code - description")."""
    qs = Item.objects.all()
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
    return [
        (i.code, f"{i.code} - {i.description}".strip())
        for i in qs.order_by("code")[:20]
    ]


__all__ = [
    "item_choices",
]

