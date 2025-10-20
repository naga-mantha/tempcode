"""Helpers for translating Gridstack payloads into layout persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Sequence

from django.db import transaction
from django.utils.text import slugify

from apps.blocks.configs import get_block_for_spec
from apps.blocks.models.layout import Layout
from apps.blocks.models.layout_block import LayoutBlock

DEFAULT_GRID_WIDTH = 4
DEFAULT_GRID_HEIGHT = 3


def _coerce_int(value: Any, default: int) -> int:
    """Best-effort conversion of ``value`` into an ``int`` with fallback."""

    try:
        if value in {None, ""}:
            raise ValueError
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return int(default)


def _coerce_mapping(value: Any) -> MutableMapping[str, Any]:
    """Normalize arbitrary payloads into a mutable mapping."""

    if isinstance(value, MutableMapping):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return dict(parsed)
    return {}


@dataclass
class LayoutGridstackSerializer:
    """Persist layout block metadata sourced from a Gridstack payload."""

    layout: Layout
    default_width: int = DEFAULT_GRID_WIDTH
    default_height: int = DEFAULT_GRID_HEIGHT
    _reserved_slugs: set[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._reserved_slugs = set(
            self.layout.layout_blocks.values_list("slug", flat=True)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save(self, nodes: Sequence[Mapping[str, Any]]) -> list[LayoutBlock]:
        """Create/update :class:`LayoutBlock` rows from ``nodes`` metadata."""

        existing = {
            block.slug: block
            for block in self.layout.layout_blocks.select_related("block")
        }
        updated: list[LayoutBlock] = []
        seen_in_payload: set[str] = set()

        with transaction.atomic():
            for index, raw in enumerate(nodes):
                if not isinstance(raw, Mapping):
                    continue

                slug = self._resolve_slug(raw, existing, seen_in_payload, index)
                seen_in_payload.add(slug)

                block_obj = existing.get(slug)
                if block_obj is None:
                    block_obj = (
                        LayoutBlock.objects.filter(layout=self.layout, slug=slug)
                        .select_related("block")
                        .first()
                    )
                block_code = self._extract_block_code(raw)

                if block_obj is None:
                    if not block_code:
                        available = ", ".join(repr(key) for key in sorted(existing.keys())) or "<none>"
                        raise ValueError(
                            "block_code/spec_id is required for new blocks"
                            f" (payload slug: {slug!r}; known slugs: {available})"
                        )
                    block_obj = LayoutBlock(
                        layout=self.layout,
                        block=get_block_for_spec(block_code),
                        slug=slug,
                    )
                elif block_code:
                    block_obj.block = get_block_for_spec(block_code)

                block_obj.order = _coerce_int(raw.get("order"), index)
                block_obj.column_index = _coerce_int(
                    raw.get("x") or raw.get("column") or raw.get("column_index"),
                    block_obj.column_index,
                )
                block_obj.row_index = _coerce_int(
                    raw.get("y") or raw.get("row") or raw.get("row_index"),
                    block_obj.row_index,
                )

                title = raw.get("title")
                if title:
                    block_obj.title = str(title)

                configuration = dict(block_obj.configuration or {})
                payload_conf = _coerce_mapping(
                    raw.get("configuration") or raw.get("settings")
                )
                if payload_conf:
                    configuration.update(payload_conf)

                grid_conf = _coerce_mapping(configuration.get("grid"))
                width = raw.get("width") or raw.get("w")
                height = raw.get("height") or raw.get("h")
                grid_conf["width"] = _coerce_int(
                    width, grid_conf.get("width", self.default_width)
                )
                grid_conf["height"] = _coerce_int(
                    height, grid_conf.get("height", self.default_height)
                )
                configuration["grid"] = grid_conf

                block_obj.configuration = configuration
                block_obj.save()

                existing[slug] = block_obj
                updated.append(block_obj)

        return updated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_slug(
        self,
        payload: Mapping[str, Any],
        existing: Mapping[str, LayoutBlock],
        seen: set[str],
        index: int,
    ) -> str:
        raw_slug = str(payload.get("slug") or payload.get("id") or "").strip()
        block_code = self._extract_block_code(payload)

        is_existing = False
        if raw_slug and raw_slug in existing:
            slug = raw_slug
            is_existing = True
        else:
            candidate = raw_slug or (block_code or f"block-{index + 1}")
            normalized = str(candidate).replace(".", "-")
            slug = slugify(normalized) or f"block-{index + 1}"

        if not is_existing and (slug in seen or slug in self._reserved_slugs):
            slug = self._next_available_slug(slug or "block", seen)

        self._reserved_slugs.add(slug)
        return slug

    def _next_available_slug(self, base: str, seen: set[str]) -> str:
        seed = slugify(base) or "block"
        counter = 2
        candidate = seed
        while candidate in self._reserved_slugs or candidate in seen:
            candidate = f"{seed}-{counter}"
            counter += 1
        return candidate

    @staticmethod
    def _extract_block_code(payload: Mapping[str, Any]) -> str | None:
        value = payload.get("block_code") or payload.get("spec_id") or payload.get("block")
        if value in {None, ""}:
            return None
        return str(value)


def get_grid_settings(
    layout_block: LayoutBlock,
    *,
    default_width: int = DEFAULT_GRID_WIDTH,
    default_height: int = DEFAULT_GRID_HEIGHT,
) -> dict[str, int]:
    """Return normalized grid metadata for ``layout_block``."""

    configuration = layout_block.configuration or {}
    grid_conf = configuration.get("grid") or {}

    width = _coerce_int(grid_conf.get("width"), default_width)
    height = _coerce_int(grid_conf.get("height"), default_height)

    return {
        "x": int(layout_block.column_index or 0),
        "y": int(layout_block.row_index or 0),
        "width": width,
        "height": height,
    }

