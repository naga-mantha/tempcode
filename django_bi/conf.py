"""Runtime access to Django BI configuration defaults."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings as django_settings

__all__ = ["settings", "DjangoBISettings"]


@dataclass
class DjangoBISettings:
    """Proxy object exposing Django settings with sensible fallbacks."""

    defaults: dict[str, Any]

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover - simple delegation
        if attr in self.defaults:
            return getattr(django_settings, attr, self.defaults[attr])
        return getattr(django_settings, attr)


settings = DjangoBISettings(
    defaults={
        "PERMISSIONS_STAFF_BYPASS": True,
        "BI_FISCAL_YEAR_START_MONTH": 1,
        "BI_FISCAL_YEAR_START_DAY": 1,
        "BLOCKS": [],
        "COMPANY_FULL_NAME": "Your Company.",
    }
)
