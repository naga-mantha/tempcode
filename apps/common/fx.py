from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db.models import Q

from apps.common.models import ExchangeRate, GlobalSettings


def get_home_currency_code(default: str = "CAD") -> str:
    obj = GlobalSettings.objects.order_by("id").first()
    return getattr(obj, "home_currency_code", None) or default


def _quantize(amount: Decimal, places: int = 2) -> Decimal:
    q = Decimal(10) ** -places
    return amount.quantize(q, rounding=ROUND_HALF_UP)


def get_rate(base: str, quote: str, date=None, strategy: str = "on_or_before") -> Optional[Decimal]:
    base = (base or "").upper()
    quote = (quote or "").upper()
    if not base or not quote:
        return None
    if base == quote:
        return Decimal("1")

    qs = ExchangeRate.objects.filter(base__code=base, quote__code=quote)
    if date:
        if strategy == "on":
            qs = qs.filter(rate_date=date)
        elif strategy == "on_or_before":
            qs = qs.filter(rate_date__lte=date)
        elif strategy == "latest":
            pass
        else:
            qs = qs.filter(rate_date__lte=date)
        qs = qs.order_by("-rate_date", "-id")
    else:
        qs = qs.order_by("-rate_date", "-id")

    row = qs.first()
    if row:
        try:
            return Decimal(row.rate)
        except Exception:
            return None

    # Try inverse pair and invert
    inv = ExchangeRate.objects.filter(base__code=quote, quote__code=base)
    if date:
        if strategy == "on":
            inv = inv.filter(rate_date=date)
        elif strategy == "on_or_before":
            inv = inv.filter(rate_date__lte=date)
    inv = inv.order_by("-rate_date", "-id").first()
    if inv:
        try:
            v = Decimal(inv.rate)
            if v == 0:
                return None
            return Decimal("1") / v
        except Exception:
            return None
    return None


def convert(amount, from_code: str, to_code: str, date=None, strategy: str = "on_or_before", places: int = 2) -> Optional[Decimal]:
    if amount is None:
        return None
    try:
        amt = Decimal(str(amount))
    except Exception:
        return None
    rate = get_rate(from_code, to_code, date=date, strategy=strategy)
    if rate is None:
        return None
    return _quantize(amt * rate, places=places)
