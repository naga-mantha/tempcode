from __future__ import annotations
from .registry import register, get_registry
from .specs import BlockSpec, Services

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

    _LOADED = True
