from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, List

from django.http import HttpRequest
from django.urls import reverse

from apps.blocks.specs import BlockSpec
from apps.policy.service import PolicyService
from apps.blocks.options import merge_table_options
from apps.blocks.services.model_table import prune_filter_schema, prune_filter_values
from apps.blocks.services.pivot_table import DefaultPivotEngine
from apps.blocks.configs import (
    get_block_for_spec,
    list_table_configs,
    choose_active_table_config,
    list_filter_configs,
    choose_active_filter_config,
    list_pivot_configs,
    choose_active_pivot_config,
)


@dataclass
class BlockController:
    spec: BlockSpec
    policy: PolicyService

    def build_context(self, request: HttpRequest, dom_ns: str | None = None) -> Dict[str, Any]:
        services = self.spec.services or None
        if not services:
            base = f"v2-{self.spec.id.replace('.', '-')}"
            dom_base = f"{base}-{dom_ns}" if dom_ns else base
            return {
                "title": self.spec.name,
                "spec_id": self.spec.id,
                "dom_id": dom_base,
                "dom_table_id": f"{dom_base}-table",
                "dom_wrapper_id": f"{dom_base}-card",
                "refresh_url": reverse("blocks:render_spec", args=[self.spec.id]),
                "data_url": reverse("blocks:data_spec", args=[self.spec.id]),
            }

        if self.spec.kind == "pivot":
            return self._build_pivot_context(request, services, dom_ns=dom_ns)

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
            filter_schema_list = prune_filter_schema(
                filter_schema_list,
                model=getattr(self.spec, "model", None),
                user=request.user,
                policy=self.policy,
            )
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
                            entry["choices_url"] = reverse("blocks:choices_spec", args=[self.spec.id, key])
                        except Exception:
                            pass
                    filter_schema[str(key)] = entry
            except Exception:
                filter_schema = {str(s.get("key")): dict(s) for s in (filter_schema_list or []) if isinstance(s, dict) and s.get("key")}

        filter_keys = list(filter_schema.keys()) if filter_schema else []
        allowed_filter_keys = filter_keys
        cleared_filter_keys = set()
        try:
            raw_cleared = request.GET.getlist("filters.__cleared")
        except Exception:
            raw_cleared = []
        allowed_filter_set = {str(k) for k in allowed_filter_keys}
        cleared_filter_keys = {str(k) for k in raw_cleared if str(k) in allowed_filter_set}
        filters = prune_filter_values(filters, allowed_filter_keys)

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
        base_filter_values = prune_filter_values(base_filter_values, allowed_filter_keys)
        if cleared_filter_keys:
            for key in cleared_filter_keys:
                base_filter_values.pop(key, None)
        # Merge order: saved config -> request overrides
        filters = {**base_filter_values, **filters}
        filters = prune_filter_values(filters, allowed_filter_keys)
        active_filter_badges: List[Dict[str, str]] = []
        for key in allowed_filter_keys:
            raw_value = filters.get(key)
            if raw_value is None:
                continue
            if isinstance(raw_value, str):
                value_text = raw_value.strip()
                if not value_text:
                    continue
            elif isinstance(raw_value, (list, tuple, set)):
                cleaned = []
                for item in raw_value:
                    if item is None:
                        continue
                    if isinstance(item, str):
                        item_text = item.strip()
                        if not item_text:
                            continue
                        cleaned.append(item_text)
                    else:
                        cleaned.append(str(item))
                if not cleaned:
                    continue
                value_text = ", ".join(cleaned)
            else:
                value_text = str(raw_value)
            entry = filter_schema.get(key, {}) or {}
            label = entry.get("label") or key
            active_filter_badges.append({
                "key": key,
                "label": str(label),
                "value": value_text,
            })


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
        pagination_mode = str(table_options.get("paginationMode", "")).lower()
        pagination_enabled = table_options.get("pagination", True)
        if pagination_mode != "remote" and pagination_enabled and services.query_builder and services.serializer:
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

        base = f"v2-{self.spec.id.replace('.', '-')}"
        dom_base = f"{base}-{dom_ns}" if dom_ns else base
        refresh_url = reverse("blocks:render_spec", args=[self.spec.id])
        data_url = reverse("blocks:data_spec", args=[self.spec.id])
        export_url = reverse("blocks:export_spec", args=[self.spec.id, "csv"])
        download_options = getattr(self.spec, "download_options", {}) or {}
        excel_download_options = dict(download_options.get("excel") or {})
        pdf_download_options = dict(download_options.get("pdf") or {})

        frontend_config = {
            "domId": dom_base,
            "wrapperId": f"{dom_base}-card",
            "tableElementId": f"{dom_base}-table",
            "specId": self.spec.id,
            "title": self.spec.name,
            "columns": columns,
            "rows": rows,
            "dataUrl": data_url,
            "filterKeys": filter_keys,
            "activeFilterBadges": active_filter_badges,
            "tableOptions": table_options,
            "activeTableConfigId": getattr(active_cfg, "id", None),
            "exportUrlTemplate": export_url,
            "excelDownloadOptions": excel_download_options,
            "pdfDownloadOptions": pdf_download_options,
        }


        return {
            "title": self.spec.name,
            "spec_id": self.spec.id,
            "columns": columns,
            "rows": rows,
            "filters": dict(filters),
            "filter_schema": filter_schema,
            "filter_keys": filter_keys,
            "active_filter_badges": active_filter_badges,
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
            "excel_download_options": excel_download_options,
            "pdf_download_options": pdf_download_options,
            "frontend_config": frontend_config,
        }

    def _build_pivot_context(self, request: HttpRequest, services, dom_ns: str | None = None) -> Dict[str, Any]:
        filter_schema_list: List[Dict[str, Any]] = []
        filter_schema: Dict[str, Any] = {}
        filters: Mapping[str, Any] = {}

        if services.filter_resolver:
            try:
                resolver = services.filter_resolver(self.spec)
            except TypeError:
                resolver = services.filter_resolver()
            filters = resolver.resolve(request)
            try:
                filter_schema_list = list(resolver.schema())
            except Exception:
                filter_schema_list = []
            filter_schema_list = prune_filter_schema(
                filter_schema_list,
                model=getattr(self.spec, "model", None),
                user=request.user,
                policy=self.policy,
            )
        if filter_schema_list:
            # Build mapping and attach AJAX choices URLs for selects, same as tables
            try:
                from django.urls import reverse as _reverse
            except Exception:
                _reverse = None
            for entry in filter_schema_list:
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key")
                if not key:
                    continue
                e = dict(entry)
                typ = e.get("type")
                if typ in {"select", "multiselect"} and _reverse:
                    try:
                        e["choices_url"] = _reverse("blocks:choices_spec", args=[self.spec.id, key])
                    except Exception:
                        pass
                filter_schema[str(key)] = e

        filter_keys = list(filter_schema.keys()) if filter_schema else []
        allowed_filter_keys = filter_keys

        try:
            raw_cleared = request.GET.getlist("filters.__cleared")
        except Exception:
            raw_cleared = []
        allowed_filter_set = {str(k) for k in allowed_filter_keys}
        cleared_filter_keys = {str(k) for k in raw_cleared if str(k) in allowed_filter_set}

        filters = prune_filter_values(filters, allowed_filter_keys)

        block_row = get_block_for_spec(self.spec.id)
        filter_configs = list(list_filter_configs(block_row, request.user))
        cfg_id = request.GET.get("filter_config_id")
        try:
            cfg_id_int = int(cfg_id) if cfg_id else None
        except ValueError:
            cfg_id_int = None
        # Mirror table behavior: if no param, fall back to user's default/public default/first
        active_filter_cfg = choose_active_filter_config(block_row, request.user, cfg_id_int)

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

        base_filter_values = getattr(active_filter_cfg, "values", {}) or {}
        if services.filter_resolver:
            try:
                cleaner = services.filter_resolver(self.spec)
            except TypeError:
                cleaner = services.filter_resolver()
            base_filter_values = cleaner.clean(base_filter_values)
        base_filter_values = prune_filter_values(base_filter_values, allowed_filter_keys)
        if cleared_filter_keys:
            for key in cleared_filter_keys:
                base_filter_values.pop(key, None)
        filters = {**base_filter_values, **filters}
        filters = prune_filter_values(filters, allowed_filter_keys)

        pivot_configs = list(list_pivot_configs(block_row, request.user))
        pivot_cfg_id = request.GET.get("pivot_config_id")
        try:
            pivot_cfg_id_int = int(pivot_cfg_id) if pivot_cfg_id else None
        except ValueError:
            pivot_cfg_id_int = None
        active_pivot_cfg = choose_active_pivot_config(block_row, request.user, pivot_cfg_id_int)

        engine_cls = getattr(services, "pivot_engine", None) or DefaultPivotEngine
        engine = engine_cls(self.spec, self.policy) if callable(engine_cls) else DefaultPivotEngine(self.spec, self.policy)
        result = engine.build(
            request,
            services,
            filters=filters,
            pivot_configs=pivot_configs,
            active_config=active_pivot_cfg,
            user=request.user,
        )
        active_pivot_cfg = result.active_config or active_pivot_cfg

        active_filter_badges: List[Dict[str, str]] = []
        for key in allowed_filter_keys:
            raw_value = filters.get(key)
            if raw_value is None:
                continue
            if isinstance(raw_value, str):
                value_text = raw_value.strip()
                if not value_text:
                    continue
            elif isinstance(raw_value, (list, tuple, set)):
                cleaned = []
                for item in raw_value:
                    if item is None:
                        continue
                    if isinstance(item, str):
                        item_text = item.strip()
                        if not item_text:
                            continue
                        cleaned.append(item_text)
                    else:
                        cleaned.append(str(item))
                if not cleaned:
                    continue
                value_text = ", ".join(cleaned)
            else:
                value_text = str(raw_value)
            entry = filter_schema.get(key, {}) or {}
            label = entry.get("label") or key
            active_filter_badges.append({
                "key": key,
                "label": str(label),
                "value": value_text,
            })

        columns_meta = list(result.columns or [])
        table_options = merge_table_options(getattr(self.spec, "table_options", {}) or {})
        download_options = getattr(self.spec, "download_options", {}) or {}
        excel_download_options = dict(download_options.get("excel") or {})
        pdf_download_options = dict(download_options.get("pdf") or {})

        base = f"v2-{self.spec.id.replace('.', '-')}"
        dom_base = f"{base}-{dom_ns}" if dom_ns else base
        refresh_url = reverse("blocks:render_spec", args=[self.spec.id])
        export_url = reverse("blocks:export_spec", args=[self.spec.id, "csv"])

        frontend_config = {
            "domId": dom_base,
            "wrapperId": f"{dom_base}-card",
            "tableElementId": f"{dom_base}-table",
            "specId": self.spec.id,
            "title": self.spec.name,
            "columns": list(
                {"key": col.get("field"), "label": col.get("title") or col.get("field") or ""}
                for col in columns_meta
            ),
            "rows": list(result.rows or []),
            "dataUrl": "",
            "filterKeys": filter_keys,
            "tableOptions": table_options,
            "activeTableConfigId": None,
            "exportUrlTemplate": export_url,
            "excelDownloadOptions": excel_download_options,
            "pdfDownloadOptions": pdf_download_options,
        }

        return {
            "title": self.spec.name,
            "spec_id": self.spec.id,
            "dom_id": dom_base,
            "dom_table_id": f"{dom_base}-table",
            "dom_wrapper_id": f"{dom_base}-card",
            "columns": columns_meta,
            "rows": list(result.rows or []),
            "pivot_configs": pivot_configs,
            "active_pivot_config_id": getattr(active_pivot_cfg, "id", None),
            "filter_configs": filter_configs,
            "active_filter_config_id": getattr(active_filter_cfg, "id", None),
            "filters": dict(filters),
            "filter_schema": filter_schema,
            "filter_keys": filter_keys,
            "filter_layout": filter_layout,
            "active_filter_badges": active_filter_badges,
            "table_options": table_options,
            "excel_download_options": excel_download_options,
            "pdf_download_options": pdf_download_options,
            "refresh_url": refresh_url,
            "data_url": "",
            "export_url_template": export_url,
            "frontend_config": frontend_config,
        }
