from __future__ import annotations
from .registry import get_registry

_LOADED = False

def load_specs() -> None:
    """Register a minimal set of specs (idempotent)."""
    global _LOADED
    if _LOADED:
        return
    # Touch the registry once so downstream imports can register specs lazily.
    get_registry()
    _LOADED = True
