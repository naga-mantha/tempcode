from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec

from .registry import register, get_registry
from .specs import BlockSpec, Services

_OPTIONAL_SPECS = (
    ("apps.layout.tables.layouts_table", "LayoutsTableSpec"),
    ("apps.common.tables.items_table", "ItemsTableSpec"),
    ("apps.common.pivots.items_pivot", "ItemsPivotSpec"),
)

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
    for module_path, attr_name in _OPTIONAL_SPECS:
        if find_spec(module_path) is None:
            continue
        module = import_module(module_path)
        spec_container = getattr(module, attr_name, None)
        block_spec = getattr(spec_container, "spec", None)
        if block_spec is None or block_spec.id in reg:
            continue
        register(block_spec)
    _LOADED = True
