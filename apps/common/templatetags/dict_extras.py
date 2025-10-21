"""Deprecated compatibility shim for Django BI template filters."""
from __future__ import annotations

import warnings

from apps.django_bi.templatetags.dict_extras import register  # noqa: F401

warnings.warn(
    "apps.common.templatetags.dict_extras is deprecated; "
    "use apps.django_bi.templatetags.dict_extras instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["register"]
