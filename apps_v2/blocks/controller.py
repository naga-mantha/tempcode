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
        filter_schema_list = []
        filter_schema: Dict[str, Any] = {}
        filter_keys = []
        if services.filter_resolver:
            # Instantiate resolver with optional spec
            try:
                resolver = services.filter_resolver(self.spec)
            except TypeError:
                resolver = services.filter_resolver()
            filters = resolver.resolve(request)
            try:
                filter_schema_list = list(resolver.schema())
            except Exception:
                filter_schema_list = []
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

        # Saved table configs (per-user) and filter layout
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

        # Build filter schema mapping and attach AJAX choices URLs for selects
        if filter_schema_list:
            try:
                from django.urls import reverse
                for s in (filter_schema_list or []):
                    if not isinstance(s, dict):
                        continue
                    key = s.get("key")
                    if not key:
                        continue
                    entry = dict(s)
                    typ = entry.get("type")
                    if typ in {"select", "multiselect"}:
                        try:
                            entry["choices_url"] = reverse("blocks_v2:choices_spec", args=[self.spec.id, key])
                        except Exception:
                            pass
                    filter_schema[str(key)] = entry
            except Exception:
                filter_schema = {str(s.get("key")): dict(s) for s in (filter_schema_list or []) if isinstance(s, dict) and s.get("key")}

        filter_keys = list(filter_schema.keys()) if filter_schema else []

        # Load user/default filter layout (if any)
        filter_layout = None
        try:
            from apps.blocks.models.block_filter_layout import BlockFilterLayout
            from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
            user_layout = BlockFilterLayout.objects.filter(block=block_row, user=request.user).first()
            admin_layout = BlockFilterLayoutTemplate.objects.filter(block=block_row).first()
            if user_layout and isinstance(user_layout.layout, dict):
                filter_layout = user_layout.layout
            elif admin_layout and isinstance(admin_layout.layout, dict):
                filter_layout = admin_layout.layout
        except Exception:
            filter_layout = None

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

        # If active config specifies columns, use only those (in order)
        if active_cfg and active_cfg.columns:
            allowed = {c.get("key") for c in columns}
            ordered = [k for k in (active_cfg.columns or []) if k in allowed]
            key_to_col = {c.get("key"): c for c in columns}
            columns = [key_to_col[k] for k in ordered if k in key_to_col]

        # Decide whether to fetch initial rows. If Tabulator uses remote pagination,
        # skip server-side row serialization on initial render for speed; the client
        # will fetch data from the JSON endpoint immediately.
        rows = []
        # Merge allowlisted Tabulator options: spec defaults + request overrides
        # Options are fixed at the spec level (per-view overrides removed)
        table_options = merge_table_options(getattr(self.spec, "table_options", {}) or {})
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
        refresh_url = reverse("blocks_v2:render_spec", args=[self.spec.id])
        data_url = reverse("blocks_v2:data_spec", args=[self.spec.id])
        export_url = reverse("blocks_v2:export_spec", args=[self.spec.id, "csv"])
        frontend_config = {
            "domId": dom_base,
            "wrapperId": f"{dom_base}-card",
            "tableElementId": f"{dom_base}-table",
            "specId": self.spec.id,
            "columns": columns,
            "rows": rows,
            "dataUrl": data_url,
            "filterKeys": filter_keys,
            "tableOptions": table_options,
            "activeTableConfigId": getattr(active_cfg, "id", None),
            "exportUrlTemplate": export_url,
        }


        return {
            "title": self.spec.name,
            "spec_id": self.spec.id,
            "columns": columns,
            "rows": rows,
            "filters": dict(filters),
            "filter_schema": filter_schema,
            "filter_keys": filter_keys,
            "filter_layout": filter_layout,
            "dom_id": dom_base,
            "dom_table_id": f"{dom_base}-table",
            "dom_wrapper_id": f"{dom_base}-card",
            "refresh_url": refresh_url,
            "data_url": data_url,
            "table_options": table_options,
            "table_configs": table_configs,
            "active_table_config_id": getattr(active_cfg, "id", None),
            "filter_configs": filter_configs,
            "active_filter_config_id": getattr(active_filter_cfg, "id", None),
            "export_url_template": export_url,
            "frontend_config": frontend_config,
        }
