"""Context processors that remain in the common app."""
from __future__ import annotations

import warnings

from django.conf import settings


def sidebar_layouts(*args, **kwargs):
    """Deprecated shim that forwards to the Django BI implementation."""
    warnings.warn(
        "apps.common.context_processors.sidebar_layouts is deprecated; "
        "use apps.django_bi.utils.context_processors.sidebar_layouts instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from apps.django_bi.utils.context_processors import (
        sidebar_layouts as _sidebar_layouts,
    )

    return _sidebar_layouts(*args, **kwargs)


def branding(request):
    """Expose company branding values to templates."""
    return {
        "company_full_name": getattr(settings, "COMPANY_FULL_NAME", "Mecaer America Inc."),
    }
