from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Optional, Tuple, List, Collection

from django.db import models

from .base import FilterResolver as BaseFilterResolver, QueryBuilder as BaseQueryBuilder, ColumnResolver as BaseColumnResolver, Serializer as BaseSerializer
from apps.policy.service import PolicyService
from apps.blocks.services.field_catalog import build_field_catalog


def _resolve_date_token(s: str, *, as_datetime: bool = False):
    """Translate simple tokens like __today__, __start_of_month__, __end_of_month__, __start_of_year__, __end_of_year__.

    Returns a date or datetime in local time (naive), or None if not a token.
    """
    if not isinstance(s, str) or not s.startswith("__"):
        return None
    from datetime import date, datetime, time, timedelta
    today = date.today()
    if s == "__today__":
        d = today
    elif s == "__start_of_month__":
        d = today.replace(day=1)
    elif s == "__end_of_month__":
        # next month start minus one day
        if today.month == 12:
            d = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            d = date(today.year, today.month + 1, 1) - timedelta(days=1)
    elif s == "__start_of_year__":
        d = date(today.year, 1, 1)
    elif s == "__end_of_year__":
        d = date(today.year, 12, 31)
    else:
        return None
    if as_datetime:
        # start of day for start tokens, end of day for end tokens
        if "start" in s:
            return datetime.combine(d, time.min)
        if "end" in s:
            return datetime.combine(d, time.max)
        return datetime.combine(d, time.min)
    return d


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
            tok = _resolve_date_token(str(v), as_datetime=False)
            if tok is not None:
                return tok
            return date.fromisoformat(str(v))
        if typ == "datetime":
            from datetime import datetime
            if isinstance(v, datetime):
                return v
            tok = _resolve_date_token(str(v), as_datetime=True)
            if tok is not None:
                return tok
            return datetime.fromisoformat(str(v))
    except Exception:
        return None
    return v


def _resolve_policy_field_target(model: Optional[type[models.Model]], path: str) -> Tuple[Optional[type[models.Model]], Optional[str]]:
    # Return the model/field pair to apply policy checks for a lookup path.
    if not model or not path:
        return None, None
    parts = [p for p in str(path).split("__") if p]
    if not parts:
        return None, None
    current_model: Optional[type[models.Model]] = model
    last_model: Optional[type[models.Model]] = None
    last_field: Optional[str] = None
    for part in parts:
        if current_model is None:
            break
        try:
            field = current_model._meta.get_field(part)
        except Exception:
            break
        last_model = current_model
        last_field = getattr(field, "name", str(part))
        remote = getattr(field, "remote_field", None)
        if remote and getattr(remote, "model", None):
            current_model = remote.model
        else:
            current_model = None
    if last_model and last_field:
        return last_model, last_field
    return None, None


def prune_filter_schema(schema_list: Sequence[Dict[str, Any]], *, model: Optional[type[models.Model]], user: Any, policy: Optional[PolicyService]) -> List[Dict[str, Any]]:
    # Filter schema entries to those allowed by policy read checks.
    if not schema_list:
        return []
    if model is None or policy is None:
        return list(schema_list)
    pruned: List[Dict[str, Any]] = []
    for entry in schema_list:
        if not isinstance(entry, dict):
            pruned.append(entry)
            continue
        key = entry.get("key")
        if not key:
            pruned.append(entry)
            continue
        field_path = entry.get("field") or key
        allowed = True
        target_model, target_field = _resolve_policy_field_target(model, field_path)
        if target_model and target_field and user is not None:
            try:
                allowed = policy.can_read_field(user, target_model, target_field, None)
            except Exception:
                allowed = True
        if allowed:
            pruned.append(entry)
    return pruned


def prune_filter_values(values: Mapping[str, Any], allowed_keys: Collection[str]) -> Dict[str, Any]:
    """Restrict a mapping of filter values to the allowed key set.

    Supports plain dicts as well as Django ``QueryDict`` instances, preserving
    multi-value lists so that __in filters continue to receive full lists.
    """

    if not values or not allowed_keys:
        return {}

    allowed_set = {str(k) for k in allowed_keys if k is not None}
    if not allowed_set:
        return {}

    cleaned: Dict[str, Any] = {}

    if hasattr(values, "lists"):
        try:
            iterator = values.lists()
        except Exception:  # pragma: no cover - defensive fallback
            iterator = values.items()
    else:
        iterator = getattr(values, "items", lambda: dict(values or {}).items())()

    for key, val in iterator:
        key_str = str(key)
        if key_str not in allowed_set:
            continue
        cleaned[key_str] = val

    return cleaned


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
            # Support both plain keys (e.g., "status") and namespaced keys (e.g., "filters.status")
            names = [str(key), f"filters.{key}"]
            raw = None
            for name in names:
                if lists and typ == "multiselect":
                    if hasattr(src, "getlist") and src.getlist(name):
                        raw = src.getlist(name)
                        break
                    val = src.get(name) if not hasattr(src, "getlist") else None
                    if val not in (None, ""):
                        raw = val
                        break
                else:
                    val = src.get(name)
                    if val not in (None, ""):
                        raw = val
                        break
            if raw is None or raw == "":
                continue
            if typ == "multiselect" and not isinstance(raw, (list, tuple)):
                # comma list fallback
                raw = [s.strip() for s in str(raw).split(",") if s.strip()]
            if isinstance(raw, (list, tuple)):
                values = []
                for item in raw:
                    coerced = _coerce_value(item, typ)
                    if coerced is None:
                        continue
                    if typ == "multiselect" and isinstance(coerced, (list, tuple)):
                        values.extend(str(x) for x in coerced if x not in (None, ""))
                    else:
                        values.append(coerced)
                # Drop empty lists to avoid filtering with __in=[] (matches nothing)
                values = [v for v in values if v not in (None, [], "")]
                if values:
                    if typ == "multiselect":
                        out[key] = values
                    else:
                        out[key] = values[0]
                else:
                    continue
            else:
                val = _coerce_value(raw, typ)
                if val is None:
                    continue
                if typ == "multiselect" and isinstance(val, (list, tuple)):
                    val = [str(v) for v in val if v not in (None, "")]
                    if not val:
                        continue
                    out[key] = val
                else:
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
