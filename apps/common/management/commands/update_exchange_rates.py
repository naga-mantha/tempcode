from __future__ import annotations

import logging
import os
from datetime import date
from time import sleep
from typing import Iterable, List, Optional, Tuple

import environ
import requests
from django.core.management.base import BaseCommand

from apps.common.models import Currency, ExchangeRate, GlobalSettings


env = environ.Env()
environ.Env.read_env()
error_logger = logging.getLogger(name="app_errors")
debug_logger = logging.getLogger(__name__)


def _get_api_key() -> Optional[str]:
    # Accept either POLYGON_API or POLYGON_API_KEY
    return env("POLYGON_API", default=None) or env("POLYGON_API_KEY", default=None) or os.getenv("POLYGON_API_KEY")


def _get_home_currency() -> str:
    obj = GlobalSettings.objects.order_by("id").first()
    code = getattr(obj, "home_currency_code", None) or "CAD"
    return code.strip().upper()


def _ensure_currency(code: str) -> Currency:
    code = (code or "").strip().upper()
    obj, _ = Currency.objects.get_or_create(code=code)
    return obj


def _fetch_polygon_prev_close(base: str, quote: str, api_key: str) -> Optional[float]:
    ticker = f"C:{base}{quote}"
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={api_key}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            debug_logger.warning("Polygon HTTP %s for %s", resp.status_code, ticker)
            return None
        data = resp.json()
        # Expect shape { results: [ { c: close, t: timestamp, ... } ], resultsCount: 1 }
        results = data.get("results") or []
        if not results:
            return None
        close = results[0].get("c")
        if close is None:
            return None
        return float(close)
    except Exception as e:
        debug_logger.warning("Polygon fetch failed for %s: %s", ticker, e)
        return None


class Command(BaseCommand):
    help = "Uploads today's exchange rates using Polygon for all currencies vs home currency."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base",
            dest="base",
            default=None,
            help="Override base currency code (default: GlobalSettings.home_currency_code or CAD)",
        )
        parser.add_argument(
            "--sleep",
            dest="sleep",
            type=float,
            default=0.5,
            help="Sleep seconds between API calls to avoid rate limits (default: 0.5)",
        )

    def handle(self, *args, **kwargs):
        api_key = _get_api_key()
        if not api_key:
            raise SystemExit("POLYGON_API or POLYGON_API_KEY not configured")

        base_code = (kwargs.get("base") or _get_home_currency()).strip().upper()
        today = date.today()

        # Collect distinct currency codes (ignore blanks and the base itself)
        codes: List[str] = [
            c.strip().upper()
            for c in Currency.objects.values_list("code", flat=True)
            if c and str(c).strip()
        ]
        codes = sorted(set(codes))
        if base_code not in codes:
            codes.append(base_code)

        base_cur = _ensure_currency(base_code)

        updated = 0
        skipped = 0
        errors = 0

        for foreign_code in codes:
            if not foreign_code:
                continue

            if foreign_code == base_code:
                # store 1:1 for base/base (optional but convenient)
                try:
                    ex, created = ExchangeRate.objects.get_or_create(
                        base=base_cur,
                        quote=base_cur,
                        rate_date=today,
                        defaults={"rate": 1.0, "source": "polygon"},
                    )
                    if not created and str(ex.rate) != str(1.0):
                        ex.rate = 1.0
                        ex.source = "polygon"
                        ex.save(update_fields=["rate", "source", "updated_at"])
                    updated += 1
                except Exception:
                    errors += 1
                continue

            foreign_cur = _ensure_currency(foreign_code)

            # We want to store base=foreign, quote=home/base
            rate = _fetch_polygon_prev_close(foreign_code, base_code, api_key)
            if rate is None:
                # Try inverse (home/foreign) and invert
                inv = _fetch_polygon_prev_close(base_code, foreign_code, api_key)
                if inv not in (None, 0):
                    try:
                        rate = 1.0 / float(inv)
                    except Exception:
                        rate = None
            if rate is None:
                skipped += 1
                continue

            try:
                ex, created = ExchangeRate.objects.get_or_create(
                    base=foreign_cur,
                    quote=base_cur,
                    rate_date=today,
                    defaults={"rate": rate, "source": "polygon"},
                )
                if not created:
                    # Update rate if different
                    try:
                        from decimal import Decimal

                        current = Decimal(str(ex.rate))
                        incoming = Decimal(str(rate))
                        if current != incoming:
                            ex.rate = incoming
                            ex.source = "polygon"
                            ex.save(update_fields=["rate", "source", "updated_at"])
                    except Exception:
                        ex.rate = rate
                        ex.source = "polygon"
                        ex.save(update_fields=["rate", "source", "updated_at"])
                updated += 1
            except Exception as e:
                errors += 1
                error_logger.error("Failed to upsert FX %s/%s: %s", foreign_code, base_code, e, exc_info=True)

            sleep(float(kwargs.get("sleep") or 0))

        debug_logger.info(
            "Exchange rates updated: updated=%s skipped=%s errors=%s base=%s date=%s",
            updated,
            skipped,
            errors,
            base_code,
            today,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Exchange rates complete. base={base_code} date={today} updated={updated} skipped={skipped} errors={errors}"
            )
        )
