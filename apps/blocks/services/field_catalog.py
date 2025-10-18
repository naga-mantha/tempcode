from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, Tuple, Dict

from django.db import models

from apps.blocks.policy import PolicyService
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
    # Caches of excluded/mandatory fields by model label (model-relative)
    excluded_by_model: Dict[str, Set[str]] = {}
    mandatory_by_model: Dict[str, Set[str]] = {}
    # Cache of root-model path-based exclusions (normalized to "__" paths)
    root_path_excluded: Set[str] = set()

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

    def is_mandatory(m: type[models.Model], field_name: str) -> bool:
        if not FieldDisplayRule:
            return False
        label = model_label(m)
        if not label:
            return False
        if label not in mandatory_by_model:
            try:
                mandatory_by_model[label] = set(
                    FieldDisplayRule.objects.for_model(label)
                    .filter(is_mandatory=True)
                    .values_list("field_name", flat=True)
                )
            except Exception:
                mandatory_by_model[label] = set()
        return field_name in mandatory_by_model.get(label, set())

    # Capture root model label for path-based mandatory rules
    root_label = None
    try:
        root_label = f"{model._meta.app_label}.{model.__name__}"
    except Exception:
        root_label = None

    def include_field(path: Tuple[str, ...], leaf_model: type[models.Model]) -> None:
        key = "__".join(path)
        leaf_name = path[-1]
        # Root path-based exclusion: skip exact-matching leaf keys
        if key in root_path_excluded:
            return
        if allow_set is not None and key not in allow_set:
            return
        if key in deny_set:
            return
        # Honor policy; allow mandatory fields regardless (parity with V1 behavior)
        # Mandatory can be declared either on the leaf model field (preferred),
        # or on the root model using a path like "fk__name" or "fk.name".
        path_mand = False
        try:
            if FieldDisplayRule and root_label:
                if root_label not in mandatory_by_model:
                    try:
                        mandatory_by_model[root_label] = set(
                            FieldDisplayRule.objects.for_model(root_label)
                            .filter(is_mandatory=True)
                            .values_list("field_name", flat=True)
                        )
                    except Exception:
                        mandatory_by_model[root_label] = set()
                root_set = mandatory_by_model.get(root_label, set())
                # Support both separators in admin entries
                path_mand = (key in root_set) or (key.replace("__", ".") in root_set)
        except Exception:
            path_mand = False
        must_include = is_mandatory(leaf_model, leaf_name) or path_mand
        try:
            if not policy.can_read_field(user, leaf_model, leaf_name, None) and not must_include:
                return
        except Exception:
            if not must_include:
                return
        try:
            leaf_field = leaf_model._meta.get_field(leaf_name)
        except Exception:
            leaf_field = None
        cols.append({
            "key": key,
            "label": _verbose_label(leaf_model, leaf_name),
            "type": _field_type(leaf_field) if leaf_field else "text",
            "mandatory": must_include,
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
                # Root path-based exclusion for relation prefixes: if the exact prefix is excluded, don't descend further
                rel_prefix = "__".join(prefix + (f.name,))
                if rel_prefix in root_path_excluded:
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
    # Initialize root path-based exclusions from FieldDisplayRule on the root model
    root_label = model_label(model)
    if FieldDisplayRule and root_label:
        try:
            # Normalize to __ paths
            root_path_excluded = set(
                (s.replace(".", "__") if isinstance(s, str) else s)
                for s in FieldDisplayRule.objects.for_model(root_label)
                          .filter(is_excluded=True)
                          .values_list("field_name", flat=True)
            )
        except Exception:
            root_path_excluded = set()
    # Kickoff
    walk(model, tuple(), 0)

    # If allow list was provided and some were not regular fields (e.g., computed), include with generic labels
    if allow_set:
        for name in allow_set:
            if name in deny_set:
                continue
            if not any(c["key"] == name for c in cols):
                # Allow explicitly requested extra key
                cols.append({"key": name, "label": name.replace("_", " ").title(), "mandatory": False})

    return cols
