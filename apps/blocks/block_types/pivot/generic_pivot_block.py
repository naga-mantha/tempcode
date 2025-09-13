from django.db.models import Count, Sum, Avg, Min, Max
from django.db.models.functions import (
    TruncDate,
    TruncMonth,
    TruncQuarter,
    TruncYear,
)

from apps.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.blocks.models.pivot_config import PivotConfig
from apps.blocks.services.filtering import apply_filter_registry
from apps.blocks.models.config_templates import PivotConfigTemplate


class GenericPivotBlock(PivotBlock):
    """User-configurable pivot with saved schemas (PivotConfig)."""

    def get_base_queryset(self, user):
        """Base queryset for the pivot prior to filters/grouping.

        Subclasses can override to scope data (e.g., status="open").
        """
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
        qs = PivotConfig.objects.filter(block=self.block, user=user)
        # Lazy seed from admin-defined template when user has no pivot configs
        if not qs.exists():
            try:
                tpl = (
                    PivotConfigTemplate.objects.filter(block=self.block, is_default=True).first()
                    or PivotConfigTemplate.objects.filter(block=self.block).first()
                )
                if tpl:
                    PivotConfig.objects.create(
                        block=self.block,
                        user=user,
                        name=tpl.name or "Default",
                        schema=dict(tpl.schema or {}),
                        is_default=True,
                    )
                    qs = PivotConfig.objects.filter(block=self.block, user=user)
            except Exception:
                pass
        active = None
        if config_id:
            try:
                active = qs.get(pk=config_id)
            except PivotConfig.DoesNotExist:
                pass
        if not active:
            active = qs.filter(is_default=True).first()
        return qs, active

    def build_columns_and_rows(self, user, filter_values):
        # Resolve active pivot config (prefer selection injected by base)
        active = getattr(self, "_active_pivot_config", None)
        configs = PivotConfig.objects.filter(block=self.block, user=user)
        if not active:
            active = configs.filter(is_default=True).first()
        if not active:
            return [], []
        # Resolve base queryset
        qs = self.get_base_queryset(user)
        if qs is None:
            return [], []

        schema = active.schema or {}
        rows = schema.get("rows", [])
        cols = schema.get("cols", [])
        measures = schema.get("measures", [])
        if not measures:
            return [], []

        # Apply registered filters then permission/state scoping (align with TableBlock)
        qs = apply_filter_registry(self.block_name, qs, filter_values or {}, user)
        try:
            from apps.permissions.checks import filter_viewable_queryset as filter_viewable_queryset_generic
            from apps.workflow.permissions import filter_viewable_queryset_state
            qs = filter_viewable_queryset_generic(user, qs)
            qs = filter_viewable_queryset_state(user, qs)
        except Exception:
            # If permission utilities unavailable for any reason, proceed without them
            pass

        # ---------------------------------------------
        # Support date bucketing for dimensions
        # rows/cols entries can be strings (field paths) or dicts
        # {"source": "<field>", "bucket": "day|month|quarter|year", "label": "...", "alias": "..."}
        # ---------------------------------------------
        def normalize_dim(entry):
            if isinstance(entry, str):
                return {
                    "source": entry,
                    "bucket": None,
                    "label": None,
                    "alias": entry,
                }
            if isinstance(entry, dict):
                src = entry.get("source") or entry.get("field")
                bucket = (entry.get("bucket") or entry.get("date_bucket") or None)
                alias = entry.get("alias") or (f"{src}__{bucket}" if bucket else src)
                return {
                    "source": src,
                    "bucket": bucket,
                    "label": entry.get("label"),
                    "alias": alias,
                }
            return None

        row_defs = [normalize_dim(r) for r in (rows or [])]
        col_defs = [normalize_dim(c) for c in (cols or [])]
        row_defs = [r for r in row_defs if r and r.get("source")]
        col_defs = [c for c in col_defs if c and c.get("source")]

        # Build annotations for any bucketed date dimensions
        annotations = {}

        def build_bucket_annotation(src, bucket):
            if not bucket:
                return None
            b = str(bucket).lower()
            if b in ("day", "date"):
                return TruncDate(src)
            if b == "month":
                return TruncMonth(src)
            if b == "quarter":
                return TruncQuarter(src)
            if b == "year":
                return TruncYear(src)
            # Unknown bucket: ignore (fallback to raw field)
            return None

        for d in [*row_defs, *col_defs]:
            expr = build_bucket_annotation(d["source"], d.get("bucket"))
            if expr is not None:
                annotations[d["alias"]] = expr

        if annotations:
            qs = qs.annotate(**annotations)

        # Build the list of group-by fields using aliases if present
        group_fields = [*(d["alias"] for d in row_defs), *(d["alias"] for d in col_defs)]
        if not group_fields:
            # No rows/cols defined: try to group by the first measure source
            group_fields = [measures[0].get("source")]
        qs = qs.values(*group_fields)

        import re
        agg_map = {}
        alias_to_title = {}
        used_aliases = set()
        for idx, m in enumerate(measures):
            src_field = m.get("source")
            agg = (m.get("agg") or "sum").lower()
            title = m.get("label") or f"{agg.upper()} {src_field}"
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
            # Normalize to date object where relevant
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

        # Collect column distinct values (supporting a single column dimension as before)
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
            # For date/datetime (or bucketed) columns, sort ascending chronologically
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
                # Map back to the corresponding row_def to format if bucketed
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
        # Row dimension columns with better titles if provided
        for i, rk in enumerate(row_keys):
            rdef = row_defs[i] if i < len(row_defs) else None
            title = (rdef.get("label") if rdef else None) or rk.replace("__", " ").title()
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
