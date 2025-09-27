from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, Tuple, Dict

from django.db import models

from apps_v2.policy.service import PolicyService
try:
    from apps.blocks.models.field_display_rule import FieldDisplayRule
except Exception:  # pragma: no cover
    FieldDisplayRule = None  # type: ignore


def _field_type(f: models.Field) -> str:
    try:
        from django.db import models as djm
        if isinstance(f, (djm.IntegerField, djm.BigIntegerField, djm.SmallIntegerField, djm.DecimalField, djm.FloatField)):
            return "number"
        if isinstance(f, (djm.BooleanField,)):
            return "boolean"
        if isinstance(f, (djm.DateField,)) and not isinstance(f, djm.DateTimeField):
            return "date"
        if isinstance(f, (djm.DateTimeField,)):
            return "datetime"
        if isinstance(f, (djm.TimeField,)):
            return "time"
        if isinstance(f, (djm.TextField, djm.CharField)):
            return "text"
    except Exception:
        pass
    return "text"


def _verbose_label(model: type[models.Model], field_name: str) -> str:
    try:
        f = model._meta.get_field(field_name)
        return getattr(f, "verbose_name", field_name).title()
    except Exception:
        return field_name.replace("_", " ").title()


def build_field_catalog(
    model: type[models.Model],
    *,
    user,
    policy: PolicyService,
    max_depth: int = 0,
    allow: Optional[Sequence[str]] = None,
    deny: Optional[Sequence[str]] = None,
) -> List[dict]:
    """Return a safe list of {key, label} columns for a model.

    - Applies PolicyService.can_read_field for flat fields
    - Enforces allow/deny lists
    - max_depth=0 supports only local fields (future: traverse relations)
    """
    allow_set: Optional[Set[str]] = set(allow) if allow else None
    deny_set: Set[str] = set(deny) if deny else set()

    cols: List[dict] = []
    # Cache of excluded fields by model label
    excluded_by_model: Dict[str, Set[str]] = {}

    def model_label(m: type[models.Model]) -> str:
        try:
            return f"{m._meta.app_label}.{m.__name__}"
        except Exception:
            return ""

    def is_excluded(m: type[models.Model], field_name: str) -> bool:
        if not FieldDisplayRule:
            return False
        label = model_label(m)
        if not label:
            return False
        if label not in excluded_by_model:
            try:
                excluded_by_model[label] = set(
                    FieldDisplayRule.objects.for_model(label)
                    .filter(is_excluded=True)
                    .values_list("field_name", flat=True)
                )
            except Exception:
                excluded_by_model[label] = set()
        return field_name in excluded_by_model.get(label, set())

    def include_field(path: Tuple[str, ...], leaf_model: type[models.Model]) -> None:
        key = "__".join(path)
        leaf_name = path[-1]
        if allow_set is not None and key not in allow_set:
            return
        if key in deny_set:
            return
        try:
            if not policy.can_read_field(user, leaf_model, leaf_name, None):
                return
        except Exception:
            return
        try:
            leaf_field = leaf_model._meta.get_field(leaf_name)
        except Exception:
            leaf_field = None
        cols.append({
            "key": key,
            "label": _verbose_label(leaf_model, leaf_name),
            "type": _field_type(leaf_field) if leaf_field else "text",
        })

    def walk(m: type[models.Model], prefix: Tuple[str, ...], depth: int):
        # At each step, include local value fields; optionally descend relations
        for f in m._meta.get_fields():
            # Skip reverse relations for catalog simplicity
            if getattr(f, "auto_created", False) and not isinstance(f, models.OneToOneRel):
                continue
            # Forward concrete fields
            if isinstance(f, models.Field) and not getattr(f, "is_relation", False):
                if is_excluded(m, f.name):
                    continue
                include_field(prefix + (f.name,), m)
                continue
            # Forward OneToOne/FK if depth allows
            if depth < max_depth and getattr(f, "is_relation", False) and not getattr(f, "many_to_many", False):
                # Forward rel: models.ForeignKey / OneToOne
                try:
                    remote = f.remote_field.model
                except Exception:
                    continue
                # If top-level field is excluded for this model, don't descend
                if is_excluded(m, f.name):
                    continue
                # Avoid infinite loops by basic cycle guard
                if remote is m and f.name in prefix:
                    continue
                # Descend
                try:
                    walk(remote, prefix + (f.name,), depth + 1)
                except Exception:
                    continue

    # Kickoff
    walk(model, tuple(), 0)

    # If allow list was provided and some were not regular fields (e.g., computed), include with generic labels
    if allow_set:
        for name in allow_set:
            if name in deny_set:
                continue
            if not any(c["key"] == name for c in cols):
                # Allow explicitly requested extra key
                cols.append({"key": name, "label": name.replace("_", " ").title()})

    return cols
