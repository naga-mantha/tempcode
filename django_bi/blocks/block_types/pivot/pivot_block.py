from django_bi.blocks.base import BaseBlock
from django_bi.blocks.models.block import Block
from django_bi.blocks.models.block_filter_config import BlockFilterConfig
from django_bi.blocks.models.config_templates import BlockFilterLayoutTemplate
from django_bi.blocks.models.block_filter_layout import BlockFilterLayout
from django_bi.blocks.services.blocks_filter_utils import FilterResolutionMixin
from django_bi.blocks.models.pivot_config import PivotConfig
from django_bi.blocks.services.filtering import apply_filter_registry
from django.contrib.admin.utils import label_for_field
from django.db.models import Count, Sum, Avg, Min, Max
from django.db.models.functions import (
    TruncDate,
    TruncMonth,
    TruncQuarter,
    TruncYear,
)
import json
import uuid


class PivotBlock(BaseBlock, FilterResolutionMixin):
    """User-configurable pivot (formerly GenericPivotBlock) with saved schemas.

    Subclasses should implement get_model() and may override get_base_queryset().
    """

    template_name = "blocks/pivot/pivot_table.html"
    supported_features = ["filters"]

    def __init__(self, block_name):
        self.block_name = block_name
        self._block = None
        self._context_cache = {}

    @property
    def block(self):
        if self._block is None:
            try:
                self._block = Block.objects.get(code=self.block_name)
            except Block.DoesNotExist:
                raise Exception(f"Block '{self.block_name}' not registered in admin.")
        return self._block

    # Subclass hooks
    def get_model(self):
        raise NotImplementedError

    def get_filter_schema(self, request):
        return {}

    # Config/data
    def render(self, request, instance_id=None):
        self._context_cache.clear()
        return super().render(request, instance_id=instance_id)

    def _get_context(self, request, instance_id):
        effective_instance_id = instance_id or self._detect_instance_id_from_query(request)
        cache_key = (id(request), effective_instance_id)
        if cache_key not in self._context_cache:
            self._context_cache[cache_key] = self._build_context(request, effective_instance_id)
        return self._context_cache[cache_key]

    def _detect_instance_id_from_query(self, request):
        try:
            keys = request.GET.keys()
        except Exception:
            return None
        prefix = f"{self.block_name}__"
        for key in keys:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix):]
            if "__" not in rest:
                continue
            candidate, tail = rest.split("__", 1)
            if (
                tail.startswith("pivot_config_id")
                or tail.startswith("filter_config_id")
                or tail.startswith("filters.")
            ):
                return candidate
        return None

    def get_config(self, request, instance_id=None):
        context = dict(self._get_context(request, instance_id))
        context.pop("data", None)
        return context

    def get_data(self, request, instance_id=None):
        context = self._get_context(request, instance_id)
        return {"data": context.get("data")}

    def get_filter_config_queryset(self, user):
        from django.db.models import Q, Case, When, IntegerField
        qs = BlockFilterConfig.objects.filter(block=self.block).filter(
            Q(user=user) | Q(visibility=BlockFilterConfig.VISIBILITY_PUBLIC)
        )
        return qs.annotate(
            _vis_order=Case(
                When(visibility=BlockFilterConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")

    def _build_context(self, request, instance_id):
        user = request.user
        filter_configs = self.get_filter_config_queryset(user)
        active_filter_config = None
        ns = f"{self.block_name}__{instance_id}__"
        filter_config_id = (
            request.GET.get(f"{ns}filter_config_id")
            or (request.GET.get(f"{self.block_name}__filter_config_id") if instance_id else None)
            or request.GET.get("filter_config_id")
        )
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                active_filter_config = None
        if not active_filter_config:
            try:
                active_filter_config = (
                    filter_configs.filter(user=user, is_default=True).first()
                    or filter_configs.filter(visibility=BlockFilterConfig.VISIBILITY_PUBLIC, is_default=True).first()
                    or filter_configs.filter(user=user).first()
                    or filter_configs.filter(visibility=BlockFilterConfig.VISIBILITY_PUBLIC).first()
                )
            except Exception:
                active_filter_config = None

        # Resolve filters
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        base_values = active_filter_config.values if active_filter_config else {}
        ns_prefix = f"{self.block_name}__{instance_id}__filters."
        selected_filter_values = self._collect_filters(request.GET, filter_schema, base=base_values, prefix=ns_prefix, allow_flat=False)

        # Resolve pivot config selection if subclass provides a selector
        pivot_configs = []
        active_pivot_config = None
        if hasattr(self, "_select_pivot_config"):
            try:
                pivot_configs, active_pivot_config = self._select_pivot_config(request, instance_id)
            except TypeError:
                pivot_configs, active_pivot_config = self._select_pivot_config(request)

        # Ensure we have an instance_id for consistent namespacing in the template
        instance_id = instance_id or uuid.uuid4().hex[:8]

        # Make active pivot config available to subclass during building
        if active_pivot_config is not None:
            setattr(self, "_active_pivot_config", active_pivot_config)
        try:
            # Subclasses build columns + data; return Tabulator config
            columns, rows = self.build_columns_and_rows(user, selected_filter_values)
        finally:
            if hasattr(self, "_active_pivot_config"):
                delattr(self, "_active_pivot_config")

        # Admin-defined filter layout
        filter_layout = self._get_filter_layout_dict()
        # Make user available for layout resolution similar to TableBlock
        self._current_user = user
        try:
            ctx = {
                "block_name": self.block_name,
                "instance_id": instance_id,
                "block_title": getattr(self.block, "name", self.block_name),
                "block": self.block,
                "filter_layout": filter_layout,
                "columns": columns,
                "data": json.dumps(rows),
                "tabulator_options": self.get_tabulator_options(user),
                "xlsx_download": json.dumps(self.get_xlsx_download_options(request, instance_id) or {}),
                "pdf_download": json.dumps(self.get_pdf_download_options(request, instance_id) or {}),
                "filter_configs": filter_configs,
                "active_filter_config_id": active_filter_config.id if active_filter_config else None,
                "pivot_configs": pivot_configs,
                "active_pivot_config_id": getattr(active_pivot_config, "id", None) if active_pivot_config else None,
                "filter_schema": filter_schema,
                "selected_filter_values": selected_filter_values,
            }
        finally:
            if hasattr(self, "_current_user"):
                delattr(self, "_current_user")
        return ctx

    def _get_filter_layout_dict(self):
        try:
            user_layout = None
            # Prefer per-user
            if hasattr(self, "_current_user") and self._current_user:
                user_layout = BlockFilterLayout.objects.filter(block=self.block, user=self._current_user).first()
            if user_layout and isinstance(user_layout.layout, dict):
                return dict(user_layout.layout)
            tpl = BlockFilterLayoutTemplate.objects.filter(block=self.block).first()
            return dict(tpl.layout or {}) if tpl and isinstance(tpl.layout, dict) else None
        except Exception:
            return None

    def get_tabulator_default_options(self, user):
        return {
            "layout": "fitDataFill",
            "pagination": "local",
            "paginationSize": 10,
            "paginationSizeSelector": [10, 20, 50, 100],
        }

    def get_tabulator_options_overrides(self, user):
        return {}

    def get_tabulator_options(self, user):
        defaults = self.get_tabulator_default_options(user) or {}
        overrides = self.get_tabulator_options_overrides(user) or {}
        return {**defaults, **overrides}

    # Default base queryset used by the generic pivot implementation
    def get_base_queryset(self, user):
        try:
            model = self.get_model()
        except Exception:
            return None
        return model.objects.all()

    def _select_pivot_config(self, request, instance_id=None):
        user = request.user
        ns = f"{self.block_name}__{instance_id}__" if instance_id else f"{self.block_name}__"
        config_id = (
            request.GET.get(f"{ns}pivot_config_id")
            or request.GET.get("pivot_config_id")
        )
        from django.db.models import Q, Case, When, IntegerField
        qs = PivotConfig.objects.filter(block=self.block).filter(
            Q(user=user) | Q(visibility=PivotConfig.VISIBILITY_PUBLIC)
        ).annotate(
            _vis_order=Case(
                When(visibility=PivotConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")
        active = None
        if config_id:
            try:
                active = qs.get(pk=config_id)
            except PivotConfig.DoesNotExist:
                pass
        if not active:
            try:
                active = (
                    qs.filter(user=user, is_default=True).first()
                    or qs.filter(visibility=PivotConfig.VISIBILITY_PUBLIC, is_default=True).first()
                    or qs.filter(user=user).first()
                    or qs.filter(visibility=PivotConfig.VISIBILITY_PUBLIC).first()
                )
            except Exception:
                active = None
        return qs, active

    # Generic pivot data engine (formerly in GenericPivotBlock)
    def build_columns_and_rows(self, user, filter_values):
        # Resolve active pivot config (prefer selection injected by base)
        active = getattr(self, "_active_pivot_config", None)
        from django.db.models import Q
        configs = PivotConfig.objects.filter(block=self.block).filter(
            Q(user=user) | Q(visibility=PivotConfig.VISIBILITY_PUBLIC)
        )
        if not active:
            active = configs.filter(is_default=True).first()
        if not active:
            return [], []
        # Resolve base queryset
        qs = self.get_base_queryset(user)
        if qs is None:
            return [], []

        schema = (active.schema or {})
        rows = schema.get("rows", [])
        cols = schema.get("cols", [])
        measures = schema.get("measures", [])
        if not measures:
            return [], []

        # Apply registered filters then permission/state scoping
        qs = apply_filter_registry(self.block_name, qs, filter_values or {}, user)
        try:
            from django_bi.permissions.checks import filter_viewable_queryset as filter_viewable_queryset_generic
            from django_bi.workflow.permissions import filter_viewable_queryset_state
            qs = filter_viewable_queryset_generic(user, qs)
            qs = filter_viewable_queryset_state(user, qs)
        except Exception:
            pass

        # Support date bucketing for dimensions
        model = self.get_model()
        try:
            from django_bi.blocks.services.column_config import get_model_fields_for_column_config
            try:
                max_depth = int(getattr(self, "get_column_config_max_depth")())
            except Exception:
                max_depth = 10
            all_meta = get_model_fields_for_column_config(model, user, max_depth=max_depth) or []
            label_map = {m.get("name"): m.get("label") for m in all_meta if m.get("name")}
        except Exception:
            label_map = {}

        def resolve_label(field_path: str) -> str:
            if field_path in label_map:
                return label_map[field_path]
            try:
                return label_for_field(field_path, model, return_attr=False)
            except Exception:
                try:
                    return field_path.replace("__", " ").replace("_", " ").title()
                except Exception:
                    return field_path

        def normalize_dim(defn):
            if isinstance(defn, str):
                return {"source": defn, "label": resolve_label(defn)}
            d = dict(defn or {})
            if d.get("source") and not d.get("label"):
                d["label"] = resolve_label(d["source"])
            return d

        row_defs = [normalize_dim(d) for d in (rows or [])]
        col_defs = [normalize_dim(d) for d in (cols or [])]

        # Apply bucket functions to queryset via annotate
        def bucketize(qs, d):
            src = (d or {}).get("source")
            bucket = (d or {}).get("bucket")
            alias = (d or {}).get("alias")
            if not src:
                return qs, None
            if bucket:
                b = str(bucket).lower()
                if b in ("day", "date"):
                    fn = TruncDate
                elif b == "month":
                    fn = TruncMonth
                elif b == "quarter":
                    fn = TruncQuarter
                elif b == "year":
                    fn = TruncYear
                else:
                    fn = None
                if fn is not None:
                    alias = alias or f"{src}__{b}"
                    qs = qs.annotate(**{alias: fn(src)})
                    return qs, alias
            return qs, (alias or src)

        for i, d in enumerate(row_defs):
            qs, alias = bucketize(qs, d)
            if alias:
                row_defs[i]["alias"] = alias
        for i, d in enumerate(col_defs):
            qs, alias = bucketize(qs, d)
            if alias:
                col_defs[i]["alias"] = alias

        # Build the list of group-by fields using aliases if present
        group_fields = [*(d["alias"] for d in row_defs), *(d["alias"] for d in col_defs)]
        if not group_fields:
            group_fields = [measures[0].get("source")]
        qs = qs.values(*group_fields)

        import re
        agg_map = {}
        alias_to_title = {}
        used_aliases = set()
        for idx, m in enumerate(measures):
            src_field = m.get("source")
            agg = (m.get("agg") or "sum").lower()
            base_field_label = resolve_label(src_field) if src_field else src_field
            title = m.get("label") or f"{agg.upper()} {base_field_label}"
            base_alias = re.sub(r"[^0-9a-zA-Z_]", "_", (m.get("label") or f"{agg}_{src_field}"))
            if re.match(r"^[0-9]", base_alias or ""):
                base_alias = f"m_{base_alias}"
            alias = base_alias or f"m_{idx}"
            suffix = 1
            while alias in used_aliases:
                alias = f"{base_alias}_{suffix}"
                suffix += 1
            used_aliases.add(alias)
            alias_to_title[alias] = title
            if agg == "sum":
                agg_map[alias] = Sum(src_field)
            elif agg == "count":
                agg_map[alias] = Count(src_field)
            elif agg == "avg":
                agg_map[alias] = Avg(src_field)
            elif agg == "min":
                agg_map[alias] = Min(src_field)
            elif agg == "max":
                agg_map[alias] = Max(src_field)
            else:
                agg_map[alias] = Sum(src_field)
        qs = qs.annotate(**agg_map)
        records = list(qs)
        if not records:
            return [], []

        # Helper to format bucketed dimension values for display
        from datetime import date, datetime as dt

        def format_dim_value(dim_def, value):
            bucket = (dim_def or {}).get("bucket")
            if not bucket:
                return value
            b = str(bucket).lower()
            if value is None:
                return value
            if isinstance(value, dt):
                vdate = value.date()
            else:
                vdate = value if isinstance(value, date) else None
            if b in ("day", "date") and vdate:
                return vdate.strftime("%Y-%m-%d")
            if b == "month" and vdate:
                return vdate.strftime("%Y-%m")
            if b == "year" and vdate:
                return str(vdate.year)
            if b == "quarter" and vdate:
                q = (vdate.month - 1) // 3 + 1
                return f"{vdate.year}-Q{q}"
            return value

        # Collect column distinct values (support single column dimension)
        col_values = []
        if col_defs:
            col_def = col_defs[0]
            col_key = col_def["alias"]
            seen = set()
            for r in records:
                v = r.get(col_key)
                if v not in seen:
                    seen.add(v)
                    col_values.append(v)
            def as_date_for_sort(v):
                if v is None:
                    return None
                if isinstance(v, dt):
                    return v.date()
                if isinstance(v, date):
                    return v
                return v
            is_bucketed_date = bool(col_def.get("bucket"))
            are_dateish = all((v is None) or isinstance(v, (date, dt)) for v in col_values)
            if is_bucketed_date or are_dateish:
                col_values.sort(key=lambda v: (v is None, as_date_for_sort(v)))

        from collections import defaultdict
        grouped = defaultdict(list)
        row_keys = [d["alias"] for d in row_defs] if row_defs else []
        for r in records:
            k = tuple(r.get(x) for x in row_keys) if row_keys else ("All",)
            grouped[k].append(r)

        data = []
        for key, items in grouped.items():
            out = {}
            for i, rk in enumerate(row_keys):
                rdef = row_defs[i] if i < len(row_defs) else None
                out[rk] = format_dim_value(rdef, key[i])
            if not col_defs:
                first = items[0]
                for alias, title in alias_to_title.items():
                    out[title] = first.get(alias)
            else:
                col_def = col_defs[0]
                col_key = col_def["alias"]
                by_col = {it.get(col_key): it for it in items}
                for raw_col_val in col_values:
                    rec = by_col.get(raw_col_val)
                    disp_val = format_dim_value(col_def, raw_col_val)
                    for alias, title in alias_to_title.items():
                        col_name = f"{disp_val} {title}"
                        out[col_name] = rec.get(alias) if rec else 0
            data.append(out)

        # Columns
        columns = []
        for i, rk in enumerate(row_keys):
            rdef = row_defs[i] if i < len(row_defs) else None
            if rdef:
                base = rdef.get("label") or resolve_label(rdef.get("source"))
                bucket = rdef.get("bucket")
                title = f"{base} ({str(bucket).capitalize()})" if bucket else base
            else:
                title = rk.replace("__", " ").title()
            columns.append({"title": title, "field": rk})
        if not col_defs:
            for alias, title in alias_to_title.items():
                columns.append({"title": title, "field": title})
        else:
            for raw_col_val in col_values:
                disp_val = format_dim_value(col_defs[0], raw_col_val)
                for alias, title in alias_to_title.items():
                    col_name = f"{disp_val} {title}"
                    columns.append({"title": col_name, "field": col_name})
        return columns, data

    # -------------------------------------------------------------
    # Download options (XLSX/PDF) similar to TableBlock
    # -------------------------------------------------------------
    def get_xlsx_download_default_options(self, request, instance_id=None):
        return {
            "filename": f"{self.block_name}.xlsx",
            "sheetName": f"{self.block_name}",
            "header": {"fillColor": "#004085", "fontColor": "#FFFFFF", "bold": True},
        }

    def get_xlsx_download_options_overrides(self, request, instance_id=None):
        return {}

    def get_xlsx_download_options(self, request, instance_id=None):
        defaults = self.get_xlsx_download_default_options(request, instance_id) or {}
        overrides = self.get_xlsx_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        # Shallow merge for nested dicts we know about
        for key in ("header", "options"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged

    def get_pdf_download_default_options(self, request, instance_id=None):
        # Keep defaults minimal; Tabulator + jsPDF options are applied client-side
        return {
            "filename": f"{self.block_name}.pdf",
            "orientation": "portrait",
            "header": {"fillColor": "#003366", "fontColor": "#FFFFFF", "bold": True},
            "options": {"jsPDF": {"unit": "pt", "format": "a4", "compress": True}},
        }

    def get_pdf_download_options_overrides(self, request, instance_id=None):
        return {}

    def get_pdf_download_options(self, request, instance_id=None):
        defaults = self.get_pdf_download_default_options(request, instance_id) or {}
        overrides = self.get_pdf_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        for key in ("header", "options"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged
