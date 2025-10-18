from __future__ import annotations

from .registry import register, get_registry
from .specs import BlockSpec, Services
from apps.layout.tables.layouts_table import LayoutsTableSpec
from apps.common.tables.items_table import ItemsTableSpec
from apps.common.pivots.items_pivot import ItemsPivotSpec

_LOADED = False


def load_specs() -> None:
    """Register a minimal set of V2 specs (idempotent)."""
    global _LOADED
    if _LOADED:
        return
    reg = get_registry()
    if "v2.hello" not in reg:
        register(
            BlockSpec(
                id="v2.hello",
                name="Hello Block (V2)",
                kind="content",
                template="blocks/hello.html",
                supported_features=(),
                services=Services(),
                category="Demo",
                description="Minimal V2 block to validate mounts and chrome.",
            )
        )
    if LayoutsTableSpec.spec.id not in reg:
        register(LayoutsTableSpec.spec)
    if ItemsTableSpec.spec.id not in reg:
        register(ItemsTableSpec.spec)
    if ItemsPivotSpec.spec.id not in reg:
        register(ItemsPivotSpec.spec)
    _LOADED = True
