from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from django.http import HttpRequest
from django.urls import reverse

from apps_v2.blocks.specs import BlockSpec
from apps_v2.policy.service import PolicyService
from apps_v2.blocks.options import merge_table_options
from apps_v2.blocks.configs import (
    get_block_for_spec,
    list_table_configs,
    choose_active_table_config,
    list_filter_configs,
    choose_active_filter_config,
)


@dataclass
class BlockController:
    spec: BlockSpec
    policy: PolicyService

    def build_context(self, request: HttpRequest) -> Dict[str, Any]:
        services = self.spec.services or None
        if not services:
            dom_base = f"v2-{self.spec.id.replace('.', '-')}"
            return {
                "title": self.spec.name,
                "spec_id": self.spec.id,
                "dom_id": dom_base,
                "dom_table_id": f"{dom_base}-table",
                "dom_wrapper_id": f"{dom_base}-card",
                "refresh_url": reverse("blocks_v2:render_spec", args=[self.spec.id]),
                "data_url": reverse("blocks_v2:data_spec", args=[self.spec.id]),
            }

        # Resolve filters
        filters: Mapping[str, Any]
        filter_schema = []
        if services.filter_resolver:
            # Instantiate resolver with optional spec
            try:
                resolver = services.filter_resolver(self.spec)
            except TypeError:
                resolver = services.filter_resolver()
            filters = resolver.resolve(request)
            try:
                filter_schema = list(resolver.schema())
            except Exception:
                filter_schema = []
        else:
            filters = {}

        # Resolve columns (if table)
        columns = []
        if services.column_resolver:
            try:
                colr = services.column_resolver(self.spec, self.policy)
            except TypeError:
                try:
                    colr = services.column_resolver(self.spec)
                except TypeError:
                    colr = services.column_resolver()
            columns = colr.get_columns(request)

        # Saved table configs (per-user)
        block_row = get_block_for_spec(self.spec.id)
        cfg_id = request.GET.get("config_id")
        try:
            cfg_id_int = int(cfg_id) if cfg_id else None
        except ValueError:
            cfg_id_int = None
        table_configs = list(list_table_configs(block_row, request.user))
        active_cfg = choose_active_table_config(block_row, request.user, cfg_id_int)

        # Saved filter configs (per-user)
        filt_cfg_id = request.GET.get("filter_config_id")
        try:
            filt_cfg_id_int = int(filt_cfg_id) if filt_cfg_id else None
        except ValueError:
            filt_cfg_id_int = None
        filter_configs = list(list_filter_configs(block_row, request.user))
        active_filter_cfg = choose_active_filter_config(block_row, request.user, filt_cfg_id_int)

        # Merge saved filter values over defaults, then apply request overrides via resolver
        base_filter_values = getattr(active_filter_cfg, "values", {}) or {}
        if services.filter_resolver:
            # Clean base values via resolver (pass spec if required)
            try:
                cleaner = services.filter_resolver(self.spec)
            except TypeError:
                cleaner = services.filter_resolver()
            base_filter_values = cleaner.clean(base_filter_values)
        # Merge order: saved config -> request overrides
        filters = {**base_filter_values, **filters}

        # If active config specifies columns, re-order and filter allowed ones
        if active_cfg and active_cfg.columns:
            allowed = {c.get("key") for c in columns}
            ordered = [k for k in (active_cfg.columns or []) if k in allowed]
            # Append any remaining allowed columns not explicitly listed
            ordered += [k for k in (c.get("key") for c in columns) if k not in ordered]
            # Rebuild columns
            key_to_col = {c.get("key"): c for c in columns}
            columns = [key_to_col[k] for k in ordered if k in key_to_col]

        # Decide whether to fetch initial rows. If Tabulator uses remote pagination,
        # skip server-side row serialization on initial render for speed; the client
        # will fetch data from the JSON endpoint immediately.
        rows = []
        # Merge allowlisted Tabulator options: spec defaults + request overrides
        request_overrides = {k: v for k, v in request.GET.items()}
        config_overrides = getattr(active_cfg, "options", {}) if active_cfg else {}
        table_options = merge_table_options(getattr(self.spec, "table_options", {}) or {}, config_overrides or {}, request_overrides)
        if str(table_options.get("pagination", "")).lower() != "remote" and services.query_builder and services.serializer:
            try:
                qb = services.query_builder(request, self.policy, self.spec)
            except TypeError:
                qb = services.query_builder(request, self.policy)
            qs = qb.get_queryset(filters)
            try:
                ser = services.serializer(self.spec)
            except TypeError:
                ser = services.serializer()
            rows = list(ser.serialize_rows(qs, columns, user=request.user, policy=self.policy))

        dom_base = f"v2-{self.spec.id.replace('.', '-')}"

        return {
            "title": self.spec.name,
            "spec_id": self.spec.id,
            "columns": columns,
            "rows": rows,
            "filters": dict(filters),
            "filter_schema": filter_schema,
            "dom_id": dom_base,
            "dom_table_id": f"{dom_base}-table",
            "dom_wrapper_id": f"{dom_base}-card",
            "refresh_url": reverse("blocks_v2:render_spec", args=[self.spec.id]),
            "data_url": reverse("blocks_v2:data_spec", args=[self.spec.id]),
            "table_options": table_options,
            "table_configs": table_configs,
            "active_table_config_id": getattr(active_cfg, "id", None),
            "filter_configs": filter_configs,
            "active_filter_config_id": getattr(active_filter_cfg, "id", None),
        }
