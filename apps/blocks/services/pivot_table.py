from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from django.contrib.admin.utils import label_for_field
from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncQuarter, TruncYear

from apps.blocks.models.pivot_config import PivotConfig
from apps.policy.service import PolicyService


@dataclass
class PivotResult:
    columns: Sequence[Dict[str, Any]]
    rows: Sequence[Dict[str, Any]]
    active_config: Optional[PivotConfig]


class DefaultPivotEngine:
    """Aggregates queryset data according to a saved pivot schema.

    The schema is expected to match the structure stored by PivotConfig:
    {
        "rows": [ {"source": "field", "label": str?, "bucket": str?} ],
        "cols": [ {"source": "field", ...} ],
        "measures": [ {"source": "field", "agg": "sum", "label": str?} ]
    }
    """

    def __init__(self, spec, policy: PolicyService):
        self.spec = spec
        self.policy = policy

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_queryset(self, request, services, filters: Mapping[str, Any]):
        qb_cls = getattr(services, "query_builder", None)
        if qb_cls:
            try:
                qb = qb_cls(request, self.policy, self.spec)
            except TypeError:
                try:
                    qb = qb_cls(request, self.policy)
                except TypeError:
                    qb = qb_cls(request)
            return qb.get_queryset(filters)
        model = getattr(self.spec, "model", None)
        if model is None:
            return None
        return model.objects.all()

    def _resolve_label(self, model: Optional[type[models.Model]], field_path: str) -> str:
        if model is None or not field_path:
            return field_path
        try:
            return label_for_field(field_path, model, return_attr=False)
        except Exception:
            return field_path.replace("__", " ").replace("_", " ").title()

    def _bucketize(self, qs, dimension: Dict[str, Any]):
        src = (dimension or {}).get("source")
        bucket = (dimension or {}).get("bucket")
        alias = (dimension or {}).get("alias")
        if not src:
            return qs, None
        if bucket:
            bucket = str(bucket).lower()
            fn = None
            if bucket in {"day", "date"}:
                fn = TruncDate
            elif bucket == "month":
                fn = TruncMonth
            elif bucket == "quarter":
                fn = TruncQuarter
            elif bucket == "year":
                fn = TruncYear
            if fn is not None:
                alias = alias or f"{src}__{bucket}"
                qs = qs.annotate(**{alias: fn(src)})
                return qs, alias
        return qs, (alias or src)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build(
        self,
        request,
        services,
        *,
        filters: Mapping[str, Any],
        pivot_configs: Iterable[PivotConfig],
        active_config: Optional[PivotConfig],
        user,
    ) -> PivotResult:
        pivot_configs = list(pivot_configs)
        if active_config is None:
            active_config = next((cfg for cfg in pivot_configs if cfg.is_default), None)
        if active_config is None:
            active_config = pivot_configs[0] if pivot_configs else None
        if active_config is None:
            return PivotResult(columns=[], rows=[], active_config=None)

        qs = self._resolve_queryset(request, services, filters)
        if qs is None:
            return PivotResult(columns=[], rows=[], active_config=active_config)

        schema = active_config.schema or {}
        row_defs = list(schema.get("rows") or [])
        col_defs = list(schema.get("cols") or [])
        measures = list(schema.get("measures") or [])
        if not measures:
            return PivotResult(columns=[], rows=[], active_config=active_config)

        # Optional integrations from v1 (filters, permissions)
        try:
            from apps.blocks.services.filtering import apply_filter_registry
        except Exception:
            apply_filter_registry = None
        if apply_filter_registry:
            try:
                qs = apply_filter_registry(self.spec.id, qs, filters or {}, user)
            except Exception:
                pass
        try:
            from apps.permissions.checks import filter_viewable_queryset as filter_viewable_queryset_generic
            qs = filter_viewable_queryset_generic(user, qs)
        except Exception:
            pass
        try:
            from apps.workflow.permissions import filter_viewable_queryset as filter_viewable_queryset_state
            qs = filter_viewable_queryset_state(user, qs)
        except Exception:
            pass

        model = getattr(self.spec, "model", None)

        def normalise_dimension(defn: Any) -> Dict[str, Any]:
            if isinstance(defn, str):
                return {"source": defn, "label": self._resolve_label(model, defn)}
            data = dict(defn or {})
            src = data.get("source")
            if src and not data.get("label"):
                data["label"] = self._resolve_label(model, src)
            return data

        row_defs = [normalise_dimension(d) for d in row_defs]
        col_defs = [normalise_dimension(d) for d in col_defs]

        for idx, dim in enumerate(row_defs):
            qs, alias = self._bucketize(qs, dim)
            if alias:
                row_defs[idx]["alias"] = alias
        for idx, dim in enumerate(col_defs):
            qs, alias = self._bucketize(qs, dim)
            if alias:
                col_defs[idx]["alias"] = alias

        row_keys = [d.get("alias") for d in row_defs if d.get("alias")]
        col_key = col_defs[0].get("alias") if col_defs else None

        group_fields = [f for f in row_keys + ([col_key] if col_key else []) if f]
        if not group_fields:
            first_measure = measures[0].get("source")
            if first_measure:
                group_fields = [first_measure]
        qs = qs.values(*group_fields)

        import re

        agg_map: Dict[str, Any] = {}
        alias_titles: Dict[str, str] = {}
        used_aliases = set()
        for idx, measure in enumerate(measures):
            src = measure.get("source")
            agg = (measure.get("agg") or "sum").lower()
            label = measure.get("label") or self._resolve_label(model, src) or src
            base_alias = measure.get("alias") or re.sub(r"[^0-9a-zA-Z_]", "_", f"{agg}_{src}" if src else f"m_{idx}")
            if base_alias and base_alias[0].isdigit():
                base_alias = f"m_{base_alias}"
            alias = base_alias or f"m_{idx}"
            suffix = 1
            while alias in used_aliases:
                alias = f"{base_alias}_{suffix}"
                suffix += 1
            used_aliases.add(alias)
            alias_titles[alias] = label or alias
            target = src or "id"
            if agg == "sum":
                agg_map[alias] = Sum(target)
            elif agg == "count":
                agg_map[alias] = Count(target)
            elif agg == "avg":
                agg_map[alias] = Avg(target)
            elif agg == "min":
                agg_map[alias] = Min(target)
            elif agg == "max":
                agg_map[alias] = Max(target)
            else:
                agg_map[alias] = Sum(target)
        qs = qs.annotate(**agg_map)
        records = list(qs)
        if not records:
            return PivotResult(columns=[], rows=[], active_config=active_config)

        from datetime import date, datetime as dt

        if row_keys:
            def _row_sort_key(rec):
                parts = []
                for idx, rk in enumerate(row_keys):
                    val = rec.get(rk)
                    dim_def = row_defs[idx] if idx < len(row_defs) else {}
                    # None should sort last; keep original type for stable ordering
                    parts.append((val is None, val))
                return tuple(parts)

            records.sort(key=_row_sort_key)

        def format_value(dim_def: Dict[str, Any], value: Any) -> Any:
            bucket = (dim_def or {}).get("bucket")
            if not bucket or value is None:
                return value
            bucket = str(bucket).lower()
            vdate: Optional[date]
            if isinstance(value, dt):
                vdate = value.date()
            elif isinstance(value, date):
                vdate = value
            else:
                vdate = None
            if not vdate:
                return value
            if bucket in {"day", "date"}:
                return vdate.strftime("%Y-%m-%d")
            if bucket == "month":
                return vdate.strftime("%Y-%m")
            if bucket == "year":
                return str(vdate.year)
            if bucket == "quarter":
                quarter = (vdate.month - 1) // 3 + 1
                return f"{vdate.year}-Q{quarter}"
            return value

        col_values = []
        if col_key:
            seen = set()
            for rec in records:
                val = rec.get(col_key)
                if val not in seen:
                    seen.add(val)
                    col_values.append(val)
            def sort_key(v):
                if v is None:
                    return (1, None)
                if isinstance(v, dt):
                    return (0, v.date())
                return (0, v)
            col_values.sort(key=sort_key)

        from collections import defaultdict
        grouped = defaultdict(list)
        for rec in records:
            key = tuple(rec.get(k) for k in row_keys) if row_keys else ("All",)
            grouped[key].append(rec)

        rows: list[Dict[str, Any]] = []
        for key, items in grouped.items():
            row = {}
            for idx, rk in enumerate(row_keys):
                dim_def = row_defs[idx] if idx < len(row_defs) else {}
                row[rk] = format_value(dim_def, key[idx])
            if not col_key:
                first = items[0]
                for alias, title in alias_titles.items():
                    row[title] = first.get(alias)
            else:
                by_col = {rec.get(col_key): rec for rec in items}
                for val in col_values:
                    formatted = format_value(col_defs[0], val)
                    rec = by_col.get(val)
                    for alias, title in alias_titles.items():
                        field = f"{formatted} {title}"
                        row[field] = rec.get(alias) if rec else 0
            rows.append(row)

        columns: list[Dict[str, Any]] = []
        for idx, rk in enumerate(row_keys):
            dim_def = row_defs[idx] if idx < len(row_defs) else {}
            label = dim_def.get("label") or self._resolve_label(model, dim_def.get("source"))
            bucket = dim_def.get("bucket")
            title = f"{label} ({bucket.capitalize()})" if bucket else label
            columns.append({"title": title, "field": rk, "key": rk, "label": title})
        if not col_key:
            for alias, title in alias_titles.items():
                columns.append({"title": title, "field": title, "key": title, "label": title})
        else:
            for val in col_values:
                formatted = format_value(col_defs[0], val)
                for alias, title in alias_titles.items():
                    field = f"{formatted} {title}"
                    columns.append({"title": field, "field": field, "key": field, "label": field})

        return PivotResult(columns=columns, rows=rows, active_config=active_config)

