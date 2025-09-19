from typing import List, Tuple, Callable, Optional

from apps.common.models import Program
from django.db.models import Q


def _apply_program_search(qs, query: str):
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
    return qs


def format_program_choices(qs, limit: int = 200) -> List[Tuple[str, str]]:
    return [
        (o.code, f"{o.code} - {o.name}".strip(" -"))
        for o in qs.order_by("code")[:limit]
    ]


def make_program_choices_for_queryset(qs_provider: Callable[[object], "models.QuerySet[Program]"]):
    def _choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        qs = qs_provider(user)
        if ids:
            qs = qs.filter(code__in=ids)
        qs = _apply_program_search(qs, query)
        return format_program_choices(qs)

    return _choices


def program_choices(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    qs = Program.objects.all()
    if ids:
        qs = qs.filter(code__in=ids)
    qs = _apply_program_search(qs, query)
    return format_program_choices(qs)


def program_choices_for_open_po(user, query: str = "", ids: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    # Program <- ItemGroup (program) <- Item (item_group) <- PurchaseOrderLine (item)
    base = Program.objects.filter(itemgroup__item__purchaseorderline__status="open").distinct()
    if ids:
        base = base.filter(code__in=ids)
    qs = _apply_program_search(base, query)
    return format_program_choices(qs)


__all__ = [
    "make_program_choices_for_queryset",
    "program_choices",
    "program_choices_for_open_po",
]

