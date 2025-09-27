from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Optional, Tuple

from django.db import models

from .base import FilterResolver as BaseFilterResolver, QueryBuilder as BaseQueryBuilder, ColumnResolver as BaseColumnResolver, Serializer as BaseSerializer
from apps_v2.policy.service import PolicyService
from apps_v2.blocks.services.field_catalog import build_field_catalog


def _coerce_value(v: Any, typ: str):
    if v is None:
        return None
    try:
        if typ in {"text", "select"}:
            return str(v)
        if typ in {"multiselect"}:
            if isinstance(v, (list, tuple)):
                return [str(x) for x in v]
            return [str(v)] if str(v) else []
        if typ == "number":
            if isinstance(v, (int, float)):
                return v
            return float(v)
        if typ == "boolean":
            if isinstance(v, bool):
                return v
            s = str(v).lower()
            return s in {"1", "true", "yes", "on"}
        if typ == "date":
            from datetime import date
            if isinstance(v, date):
                return v
            return date.fromisoformat(str(v))
        if typ == "datetime":
            from datetime import datetime
            if isinstance(v, datetime):
                return v
            return datetime.fromisoformat(str(v))
    except Exception:
        return None
    return v


class SchemaFilterResolver(BaseFilterResolver):
    """Filter resolver driven by BlockSpec.filter_schema."""

    def __init__(self, spec):
        self.spec = spec

    def schema(self) -> Sequence[Dict[str, Any]]:
        return list(getattr(self.spec, "filter_schema", []) or [])

    def _iter_fields(self) -> Iterable[Dict[str, Any]]:
        for f in self.schema():
            if isinstance(f, dict) and f.get("key"):
                yield f

    def _read(self, src: Mapping[str, Any], *, lists: bool = False) -> Mapping[str, Any]:
        out: Dict[str, Any] = {}
        for f in self._iter_fields():
            key = f.get("key")
            typ = f.get("type", "text")
            if lists and typ == "multiselect":
                raw = src.getlist(key) if hasattr(src, "getlist") else src.get(key)
            else:
                raw = src.get(key)
            if raw is None or raw == "":
                continue
            if typ == "multiselect" and not isinstance(raw, (list, tuple)):
                # comma list fallback
                raw = [s.strip() for s in str(raw).split(",") if s.strip()]
            if isinstance(raw, (list, tuple)):
                coerced = [_coerce_value(v, typ) for v in raw]
                coerced = [v for v in coerced if v is not None]
                # Drop empty lists to avoid filtering with __in=[] (matches nothing)
                if coerced:
                    out[key] = coerced
                else:
                    continue
            else:
                val = _coerce_value(raw, typ)
                if val is not None:
                    out[key] = val
        return out

    def resolve(self, request) -> Mapping[str, Any]:
        return self._read(request.GET, lists=True)

    def clean(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
        values = values or {}
        return self._read(values, lists=False)


class ModelQueryBuilder(BaseQueryBuilder):
    """Query builder for spec.model using schema lookups."""

    def __init__(self, request, policy: PolicyService, spec):
        self.request = request
        self.policy = policy
        self.spec = spec

    def get_queryset(self, filters: Mapping[str, Any]):
        model: type[models.Model] = getattr(self.spec, "model", None)
        if model is None:
            return []
        qs = model.objects.all()
        schema = list(getattr(self.spec, "filter_schema", []) or [])
        # Build mapping for lookups
        by_key = {f.get("key"): f for f in schema if isinstance(f, dict) and f.get("key")}
        for key, value in (filters or {}).items():
            # Skip empty lists to avoid __in=[]
            if isinstance(value, (list, tuple)) and not value:
                continue
            entry = by_key.get(key) or {}
            # Model field path to filter on
            field_path = entry.get("field") or key
            # Support explicit lookup path (e.g., created_at__date__gte)
            lookup = None
            lookups_map = entry.get("lookups") or {}
            if key in lookups_map:
                lookup = lookups_map.get(key)
            if not lookup:
                # Default lookup based on type
                typ = entry.get("type", "text")
                if typ == "text":
                    lookup = f"{field_path}__icontains"
                elif typ == "number":
                    lookup = f"{field_path}__exact"
                elif typ == "boolean":
                    lookup = f"{field_path}__exact"
                elif typ == "date":
                    lookup = f"{field_path}__date__exact"
                elif typ == "datetime":
                    lookup = f"{field_path}__exact"
                elif typ == "multiselect":
                    lookup = f"{field_path}__in"
                else:  # select
                    lookup = f"{field_path}__exact"
            try:
                qs = qs.filter(**{lookup: value})
            except Exception:
                # Skip invalid filters instead of blowing up
                continue
        # Apply permissive policy scoping
        qs = self.policy.filter_queryset(self.request.user, qs)
        return qs


class ModelColumnResolver(BaseColumnResolver):
    def __init__(self, spec, policy: Optional[PolicyService] = None):
        self.spec = spec
        self.policy = policy or PolicyService()

    def get_columns(self, request) -> Sequence[Dict[str, Any]]:
        model = getattr(self.spec, "model", None)
        if model is None:
            return []
        return build_field_catalog(
            model,
            user=request.user,
            policy=self.policy,
            max_depth=getattr(self.spec, "column_max_depth", 0) or 0,
            allow=getattr(self.spec, "column_allow", None),
            deny=getattr(self.spec, "column_deny", None),
        )


def _resolve_leaf_model(model: type[models.Model], path: str) -> Tuple[type[models.Model], str]:
    parts = (path or "").split("__")
    m = model
    for name in parts[:-1]:
        try:
            f = m._meta.get_field(name)
            m = f.remote_field.model  # type: ignore[attr-defined]
        except Exception:
            break
    return m, parts[-1] if parts else ""


class ModelSerializer(BaseSerializer):
    def __init__(self, spec):
        self.spec = spec

    def _get_value(self, obj: Any, path: str):
        cur = obj
        for name in (path or "").split("__"):
            if cur is None:
                return None
            try:
                cur = getattr(cur, name)
            except Exception:
                try:
                    cur = cur.get(name)
                except Exception:
                    return None
        # Normalize common types
        try:
            from datetime import date, datetime, time
            if isinstance(cur, (date, datetime, time)):
                return cur.isoformat()
        except Exception:
            pass
        try:
            if isinstance(cur, models.Model):
                return str(cur)
        except Exception:
            pass
        return cur

    def serialize_rows(
        self,
        qs,
        columns: Sequence[Dict[str, Any]],
        *,
        user: Any = None,
        policy: Any = None,
    ) -> Iterable[Dict[str, Any]]:
        model = getattr(self.spec, "model", None)
        keys = [c.get("key") for c in (columns or [])]
        for obj in qs:
            row: Dict[str, Any] = {}
            for key in keys:
                leaf_model, leaf_field = _resolve_leaf_model(model, key) if model else (model, key)
                try:
                    if policy and user and not policy.can_read_field(user, leaf_model, leaf_field, obj):
                        row[key] = "***"
                        continue
                except Exception:
                    row[key] = "***"
                    continue
                val = self._get_value(obj, key)
                row[key] = val if val is not None else ""
            yield row
