from __future__ import annotations

from typing import Dict, Iterable, Sequence, Any
import logging

from django.template import loader

from .specs import BlockSpec
from apps.blocks.options import ALLOWED_OPTIONS as TABLE_ALLOWED_OPTIONS

log = logging.getLogger(__name__)


_REGISTRY: Dict[str, BlockSpec] = {}


ALLOWED_KINDS = {"table", "pivot", "chart", "content"}
ALLOWED_FEATURES = {"filters", "column_config", "export", "inline_edit", "drilldown"}


def _validate_spec(spec: BlockSpec) -> None:
    # Kind
    if spec.kind not in ALLOWED_KINDS:
        raise ValueError(f"Invalid BlockSpec.kind '{spec.kind}' for {spec.id}")
    # Template exists
    if not spec.template:
        raise ValueError(f"BlockSpec.template is required for {spec.id}")
    try:
        loader.get_template(spec.template)
    except Exception as e:
        raise ValueError(f"Template not found for {spec.id}: {spec.template}") from e
    # Supported features sanity
    feats: Sequence[str] = list(spec.supported_features or ())
    unknown = [f for f in feats if f not in ALLOWED_FEATURES]
    if unknown:
        raise ValueError(f"Unsupported features in {spec.id}: {unknown}")
    # Table options allowlist
    opts = getattr(spec, "table_options", None) or {}
    bad = [k for k in opts.keys() if k not in TABLE_ALLOWED_OPTIONS]
    if bad:
        raise ValueError(f"Unsupported table_options in {spec.id}: {bad}")
    # Service presence for tables
    if spec.kind == "table":
        services = spec.services or None
        if not services:
            raise ValueError(f"Table spec {spec.id} must provide services")
        if not getattr(services, "column_resolver", None):
            raise ValueError(f"Table spec {spec.id} is missing column_resolver")
        if not getattr(services, "query_builder", None):
            raise ValueError(f"Table spec {spec.id} is missing query_builder")
        if not getattr(services, "serializer", None):
            raise ValueError(f"Table spec {spec.id} is missing serializer")
        # If using generic Model* services, ensure model is provided
        try:
            from apps.blocks.services.model_table import ModelColumnResolver, ModelQueryBuilder
            if services.column_resolver in {ModelColumnResolver} or services.query_builder in {ModelQueryBuilder}:
                if getattr(spec, "model", None) is None:
                    raise ValueError(f"Table spec {spec.id} uses Model* services but has no model")
        except Exception:
            # If import fails, skip this specific check
            pass
        # Depth should be >= 0
        depth = getattr(spec, "column_max_depth", 0)
        if not isinstance(depth, int) or depth < 0:
            raise ValueError(f"column_max_depth must be >= 0 for {spec.id}")
    elif spec.kind == "pivot":
        services = spec.services or None
        if not services:
            raise ValueError(f"Pivot spec {spec.id} must provide services")
        if not getattr(services, "pivot_engine", None):
            raise ValueError(f"Pivot spec {spec.id} is missing pivot_engine")
        if getattr(spec, "model", None) is None:
            raise ValueError(f"Pivot spec {spec.id} must declare a model")


def register(spec: BlockSpec) -> None:
    if spec.id in _REGISTRY:
        raise ValueError(f"Duplicate BlockSpec id: {spec.id}")
    _validate_spec(spec)
    _REGISTRY[spec.id] = spec


def get_registry() -> Dict[str, BlockSpec]:
    return dict(_REGISTRY)


# Compatibility shim for legacy v1-style registrars that expect a
# `block_registry` object with a `register(code, block)` method.
# In the v2 system, specs are the source of truth; we no-op legacy
# registrations to avoid import crashes during AppConfig.ready hooks.
class _LegacyBlockRegistry:
    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def register(self, code: str, block: Any) -> None:
        # Accept and store, but do not surface into v2 registry.
        try:
            self._data[str(code)] = block
        except Exception:
            pass


block_registry = _LegacyBlockRegistry()

