from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from django.urls import reverse

from apps.blocks.configs import get_block_for_spec
from apps.blocks.models.layout import Layout, VisibilityChoices
from apps.blocks.models.layout_filter_config import LayoutFilterConfig
from apps.blocks.policy import PolicyService
from apps.blocks.register import load_specs
from apps.blocks.registry import get_registry
from apps.blocks.services.model_table import prune_filter_schema, prune_filter_values


@dataclass(frozen=True)
class LayoutFilterBlockMetadata:
    """Metadata describing the filter UI for a layout block."""

    slug: str
    title: str
    spec_id: str
    spec_name: str
    filter_schema: Dict[str, Dict[str, Any]]
    filter_layout: Mapping[str, Any] | None
    initial_values: Dict[str, Any]

    @property
    def has_filters(self) -> bool:
        return bool(self.filter_schema)


def list_layout_filter_configs(layout: Layout, user) -> Sequence[LayoutFilterConfig]:
    """Return saved layout filter configs visible to ``user``."""

    qs = layout.filter_configs.select_related("owner").order_by("name")
    if user.is_staff or user == layout.owner:
        return list(qs)
    return list(qs.filter(visibility=VisibilityChoices.PUBLIC))


def choose_layout_filter_config(
    layout: Layout,
    user,
    *,
    identifier: Optional[str] = None,
    configs: Optional[Sequence] = None,
) -> Any:
    """Select the appropriate layout filter config for ``identifier``."""

    configs = list(configs or list_layout_filter_configs(layout, user))
    if identifier:
        normalized = str(identifier).strip()
        if normalized and normalized not in {"__none__", "__clear__"}:
            match = next(
                (
                    cfg
                    for cfg in configs
                    if str(cfg.slug) == normalized or str(cfg.pk) == normalized
                ),
                None,
            )
            if match is not None:
                return match
    # fall back to the owner's default config if present
    default_cfg = next((cfg for cfg in configs if getattr(cfg, "is_default", False)), None)
    if default_cfg is not None:
        return default_cfg
    return configs[0] if configs else None


def extract_layout_filter_values(config) -> Dict[str, Dict[str, Any]]:
    """Normalize the stored values for ``config`` into a per-block mapping."""

    if not config:
        return {}
    values = getattr(config, "values", {}) or {}
    if isinstance(values, Mapping):
        blocks = values.get("blocks") if "blocks" in values else values
    else:
        blocks = {}
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(blocks, Mapping):
        return result
    for slug, payload in blocks.items():
        if not isinstance(payload, Mapping):
            continue
        filters = payload.get("filters") if "filters" in payload else payload
        if not isinstance(filters, Mapping):
            continue
        cleaned: Dict[str, Any] = {}
        for key, value in filters.items():
            key_str = str(key)
            if isinstance(value, list):
                cleaned[key_str] = list(value)
            elif isinstance(value, tuple):
                cleaned[key_str] = list(value)
            else:
                cleaned[key_str] = value
        result[str(slug)] = cleaned
    return result


def parse_request_filter_overrides(request) -> Dict[str, Dict[str, Any]]:
    """Extract per-block overrides from ``request.GET``."""

    overrides: Dict[str, Dict[str, Any]] = {}
    query = getattr(request, "GET", None)
    if not query:
        return overrides
    for key in query.keys():
        if not isinstance(key, str) or not key.startswith("filters__"):
            continue
        parts = key.split("__", 2)
        if len(parts) != 3:
            continue
        _, slug, field = parts
        if not slug or not field:
            continue
        raw_values = query.getlist(key)
        if not raw_values:
            continue
        cleaned_values = [v for v in raw_values if v not in (None, "")]
        if not cleaned_values:
            continue
        if len(cleaned_values) == 1:
            value: Any = cleaned_values[0]
        else:
            value = cleaned_values
        overrides.setdefault(slug, {})[field] = value
    return overrides


def merge_layout_filter_values(
    base: Mapping[str, Mapping[str, Any]] | None,
    overrides: Mapping[str, Mapping[str, Any]] | None,
) -> Dict[str, Dict[str, Any]]:
    """Merge ``overrides`` on top of ``base`` preserving nested mappings."""

    merged: Dict[str, Dict[str, Any]] = {}
    for slug, payload in (base or {}).items():
        merged[str(slug)] = {str(k): v for k, v in (payload or {}).items()}
    for slug, payload in (overrides or {}).items():
        block = merged.setdefault(str(slug), {})
        for key, value in (payload or {}).items():
            block[str(key)] = value
    return merged


def aggregate_layout_filter_metadata(
    layout: Layout,
    *,
    user,
    policy: Optional[PolicyService] = None,
    values: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Sequence[LayoutFilterBlockMetadata]:
    """Combine filter schema + values for each block in ``layout``."""

    load_specs()
    registry = get_registry()
    policy = policy or PolicyService()

    results: list[LayoutFilterBlockMetadata] = []
    values = values or {}

    layout_blocks = list(
        layout.layout_blocks.select_related("block").order_by("order", "pk")
    )

    for block in layout_blocks:
        spec = registry.get(block.block.code)
        if spec is None:
            continue
        services = getattr(spec, "services", None)
        resolver_cls = getattr(services, "filter_resolver", None) if services else None
        if not resolver_cls:
            continue
        try:
            try:
                resolver = resolver_cls(spec)
            except TypeError:
                resolver = resolver_cls()
            schema_list = list(resolver.schema())
        except Exception:
            schema_list = []
        schema_list = prune_filter_schema(
            schema_list,
            model=getattr(spec, "model", None),
            user=user,
            policy=policy,
        )
        if not schema_list:
            continue
        schema: Dict[str, Dict[str, Any]] = {}
        for entry in schema_list:
            if not isinstance(entry, Mapping):
                continue
            key = entry.get("key")
            if not key:
                continue
            data = dict(entry)
            typ = data.get("type")
            if typ in {"select", "multiselect"}:
                try:
                    data["choices_url"] = reverse(
                        "blocks:choices_spec",
                        args=[spec.id, key],
                    )
                except Exception:
                    pass
            schema[str(key)] = data

        filter_layout = None
        try:
            from apps.blocks.models.block_filter_layout import BlockFilterLayout
            from apps.blocks.models.config_templates import BlockFilterLayoutTemplate

            block_row = get_block_for_spec(spec.id)
            user_layout = (
                BlockFilterLayout.objects.filter(block=block_row, user=user).first()
                if block_row
                else None
            )
            admin_layout = (
                BlockFilterLayoutTemplate.objects.filter(block=block_row).first()
                if block_row
                else None
            )
            if user_layout and isinstance(user_layout.layout, Mapping):
                filter_layout = user_layout.layout
            elif admin_layout and isinstance(admin_layout.layout, Mapping):
                filter_layout = admin_layout.layout
        except Exception:
            filter_layout = None

        allowed_keys = schema.keys()
        block_values = prune_filter_values(values.get(block.slug) or {}, allowed_keys)
        cleaned_values: Dict[str, Any] = {}
        for key, value in (block_values or {}).items():
            if isinstance(value, (list, tuple)):
                cleaned_values[str(key)] = list(value)
            else:
                cleaned_values[str(key)] = value

        results.append(
            LayoutFilterBlockMetadata(
                slug=block.slug,
                title=block.title or block.block.name,
                spec_id=spec.id,
                spec_name=getattr(spec, "name", block.block.name),
                filter_schema=schema,
                filter_layout=filter_layout,
                initial_values=cleaned_values,
            )
        )

    return results
