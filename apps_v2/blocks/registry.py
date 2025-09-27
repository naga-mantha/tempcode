from __future__ import annotations

from typing import Dict

from .specs import BlockSpec


_REGISTRY: Dict[str, BlockSpec] = {}


def register(spec: BlockSpec) -> None:
    if spec.id in _REGISTRY:
        raise ValueError(f"Duplicate BlockSpec id: {spec.id}")
    # Basic validation: ensure template path and kind are present
    if not spec.template:
        raise ValueError("BlockSpec.template is required")
    _REGISTRY[spec.id] = spec


def get_registry() -> Dict[str, BlockSpec]:
    return dict(_REGISTRY)

