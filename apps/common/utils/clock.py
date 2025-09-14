from __future__ import annotations

from datetime import date, datetime
from django.utils import timezone


def now() -> datetime:
    """Return current timezone-aware datetime.

    Uses Django's timezone utilities to respect settings.TIME_ZONE and
    ensure returned datetimes are aware.
    """
    return timezone.now()


def today() -> date:
    """Return current local date for the configured time zone.

    Wrapper around timezone.localdate() to avoid naive date.today() and
    keep a single import point across the project.
    """
    return timezone.localdate()

