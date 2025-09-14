from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models, transaction


@dataclass
class ImportResult:
    total: int
    created: int
    updated: int
    skipped: int
    errors: int


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return True
    except Exception:
        pass
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() in {"nan", "none", "null"}:
            return True
    return False


def _coerce_value_for_field(field: models.Field, value: Any) -> Any:
    try:
        from datetime import datetime, date
        if isinstance(field, models.DateField) and not isinstance(field, models.DateTimeField):
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                s = value.strip()
                if ' ' in s:
                    s = s.split(' ')[0]
                if 'T' in s:
                    s = s.split('T')[0]
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        pass
                return s
        if isinstance(field, models.DateTimeField):
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            if isinstance(value, str):
                s = value.strip()
                try:
                    return datetime.fromisoformat(s)
                except Exception:
                    pass
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y'):
                    try:
                        dt = datetime.strptime(s, fmt)
                        if fmt in ('%Y-%m-%d', '%m/%d/%Y'):
                            return datetime.combine(dt.date(), datetime.min.time())
                        return dt
                    except Exception:
                        pass
                return s
    except Exception:
        return value
    return value


def _get_unique_constraints(model: models.Model) -> List[Tuple[str, ...]]:
    opts = model._meta
    uniques: List[Tuple[str, ...]] = []
    # legacy unique_together
    for ut in (getattr(opts, "unique_together", None) or []):
        if isinstance(ut, (list, tuple)):
            uniques.append(tuple(ut))
    # UniqueConstraint
    for c in getattr(opts, "constraints", []) or []:
        try:
            from django.db.models import UniqueConstraint
            if isinstance(c, UniqueConstraint):
                uniques.append(tuple(c.fields or ()))
        except Exception:
            continue
    # Single-field uniques
    for f in opts.fields:
        if getattr(f, "unique", False):
            uniques.append((f.name,))
    # de-dup while preserving order
    seen = set()
    out = []
    for u in uniques:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def import_rows_from_text(
    *,
    model: Union[str, models.Model],
    file_path: str,
    delimiter: str = "|",
    has_header: bool = False,
    ignore_prefixes: Optional[Iterable[str]] = None,
    mapping: Mapping[Union[str, int], str],
    value_map: Optional[Mapping[Union[str, int], Mapping[Any, Any]]] = None,
    method: str = "bulk_create",  # or "save_per_instance"
    unique_fields: Optional[Sequence[str]] = None,
    chunk_size: int = 1000,
    dry_run: bool = False,
    recalc: Optional[Union[str, Iterable[str]]] = None,
    recalc_exclude: Optional[Iterable[str]] = None,
    stop_on_duplicate: bool = True,
    encoding: Optional[str] = None,
    encoding_errors: str = "strict",
    override_fields: Optional[Mapping[str, Any]] = None,
    relation_override_fields: Optional[Mapping[str, Mapping[str, Any]]] = None,
    recalc_always_save: bool = False,
) -> ImportResult:
    """Import rows into a model from a delimited text file.

    - mapping: column key -> model field path. If has_header, keys are header names; otherwise keys are indices.
    - unique_fields: fields that identify a row (used for upsert and duplicate detection). If not provided, the first
      detected unique constraint on the model is used. If none found and stop_on_duplicate is True, a ValueError is raised.
    - method: "bulk_create" for fast upsert (no save/signals), or "save_per_instance" to call save() per row.
    """

    # Resolve model class if a label is provided
    if isinstance(model, str):
        try:
            app_label, model_name = model.split(".")
            Model = django_apps.get_model(app_label, model_name)
        except Exception as exc:
            raise ImproperlyConfigured(f"Invalid model label '{model}': {exc}")
    else:
        Model = model  # type: ignore[assignment]

    ignore_prefixes = list(ignore_prefixes or [])
    value_map = value_map or {}

    # Read file with encoding fallback
    def _read_lines(path: str, enc: str, errs: str) -> List[str]:
        with open(path, "r", encoding=enc, errors=errs) as fh:
            return [ln.rstrip("\n\r") for ln in fh.readlines()]

    if encoding:
        raw_lines = _read_lines(file_path, encoding, encoding_errors)
    else:
        raw_lines = []
        last_err: Optional[Exception] = None
        for enc_try in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                raw_lines = _read_lines(file_path, enc_try, "strict")
                last_err = None
                break
            except UnicodeDecodeError as e:
                last_err = e
                continue
        if last_err is not None and not raw_lines:
            # As a final fallback, try replacing invalid bytes using utf-8
            raw_lines = _read_lines(file_path, "utf-8", "replace")

    # Filter lines by prefixes
    data_lines: List[str] = []
    header_cols: List[str] = []
    if has_header and raw_lines:
        header_cols = [h.strip() for h in raw_lines[0].split(delimiter)]
        raw_lines = raw_lines[1:]

    for ln in raw_lines:
        if any(ln.startswith(pfx) for pfx in ignore_prefixes):
            continue
        if not ln.strip():
            continue
        data_lines.append(ln)

    # Resolve mapping keys into column indices
    def _col_index(key: Union[str, int]) -> Optional[int]:
        if has_header and not str(key).isdigit():
            try:
                return header_cols.index(str(key))
            except ValueError:
                return None
        try:
            return int(key)
        except Exception:
            return None

    # Prepare model field map
    field_map: Dict[str, models.Field] = {f.name: f for f in Model._meta.get_fields() if hasattr(f, 'attname')}

    # Choose unique fields for upsert and duplicate detection
    if unique_fields and len(unique_fields) > 0:
        unique_fields_tuple: Tuple[str, ...] = tuple(unique_fields)
    else:
        uniques = _get_unique_constraints(Model)
        if not uniques:
            if stop_on_duplicate:
                raise ValueError(
                    "No unique constraints found on model and unique_fields not provided; cannot enforce duplicate detection."
                )
            unique_fields_tuple = tuple()
        else:
            unique_fields_tuple = uniques[0]

    # Prepare rows
    total = 0
    created = 0
    updated = 0
    skipped = 0
    errors = 0

    # Preparse all rows into assignments and identity keys, detect duplicates in input
    parsed: List[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]] = []
    seen_keys: set = set()

    for line in data_lines:
        total += 1
        parts = [p.strip() for p in line.split(delimiter)]
        try:
            assignments: Dict[str, Any] = {}
            rel_constraints: Dict[str, Dict[str, Any]] = {}

            for key, path in mapping.items():
                idx = _col_index(key)
                if idx is None or idx < 0 or idx >= len(parts):
                    continue
                raw_value: Any = parts[idx]

                # Apply value transform per column key
                try:
                    col_map = value_map.get(key) if isinstance(value_map, dict) else None  # type: ignore[index]
                    if isinstance(col_map, dict):
                        if raw_value in col_map:
                            raw_value = col_map[raw_value]
                        elif isinstance(raw_value, str):
                            low = raw_value.strip().lower()
                            for k, v in col_map.items():
                                if isinstance(k, str) and k.strip().lower() == low:
                                    raw_value = v
                                    break
                except Exception:
                    pass

                if _is_null(raw_value):
                    continue

                if "__" in path:
                    root_field, *subpath = path.split("__")
                    fobj = field_map.get(root_field)
                    if not fobj or not (hasattr(fobj, 'remote_field') and fobj.remote_field):
                        raise ValueError(f"Mapping points to relation '{root_field}' which is not a ForeignKey/OneToOne")
                    if root_field not in rel_constraints:
                        rel_constraints[root_field] = {}
                    lookup_field = "__".join(subpath)
                    if lookup_field == "":
                        lookup_field = "pk"
                    rel_constraints[root_field][lookup_field] = raw_value
                else:
                    fobj = field_map.get(path)
                    if fobj is not None:
                        raw_value = _coerce_value_for_field(fobj, raw_value)
                    assignments[path] = raw_value

            # Compute identity key for duplicate detection, including relation constraints
            if unique_fields_tuple:
                identity_values: List[Any] = []
                for f in unique_fields_tuple:
                    if f in assignments:
                        identity_values.append(assignments.get(f))
                    elif f in rel_constraints:
                        cons = rel_constraints[f]
                        # Prefer a single specific lookup value if available
                        if "pk" in cons:
                            identity_values.append(cons["pk"])
                        elif len(cons) == 1:
                            identity_values.append(next(iter(cons.values())))
                        else:
                            # Fallback: stable representation of constraints
                            identity_values.append(tuple(sorted(cons.items())))
                    else:
                        identity_values.append(None)
                key_tuple = tuple(identity_values)
                if key_tuple in seen_keys:
                    raise ValueError(f"Duplicate input row detected for unique key {unique_fields_tuple}={key_tuple!r}")
                seen_keys.add(key_tuple)

            parsed.append((assignments, rel_constraints))
        except Exception:
            errors += 1
            continue

    if dry_run:
        return ImportResult(total=total, created=created, updated=updated, skipped=skipped, errors=errors)

    # Two modes: bulk_create (with upsert) or save_per_instance
    method = (method or "bulk_create").lower()

    def _sanitize_rel_constraints(rel_model: models.Model, constraints: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, val in constraints.items():
            if isinstance(val, str):
                val = val.strip()
            # Special handling for Currency.code normalization
            try:
                if rel_model.__name__ == "Currency":
                    # Normalize code to uppercase and respect max_length
                    field_name = key.split("__", 1)[0] if key else "code"
                    if field_name == "code" and isinstance(val, str):
                        max_len = getattr(rel_model._meta.get_field("code"), "max_length", 5)
                        val = val.upper()[: max_len or 5]
            except Exception:
                pass
            out[key] = val
        return out

    if method == "bulk_create":
        # Build instances first, resolving relations
        instances: List[models.Model] = []
        for assignments, rel_constraints in parsed:
            try:
                # Resolve relations
                for root_field, constraints in rel_constraints.items():
                    fobj = field_map.get(root_field)
                    rel_model = fobj.remote_field.model  # type: ignore[attr-defined]
                    constraints = _sanitize_rel_constraints(rel_model, constraints)
                    rel_instance = rel_model.objects.filter(**constraints).first()
                    if not rel_instance:
                        # Create missing related record (supports one nested level via __)
                        create_kwargs: Dict[str, Any] = {}
                        for key, val in constraints.items():
                            if "__" not in key or key == "pk":
                                field_name = key if key != "pk" else rel_model._meta.pk.name
                                create_kwargs[field_name] = val
                                continue
                            parts_path = key.split("__")
                            base_field_name = parts_path[0]
                            nested_lookup = "__".join(parts_path[1:])
                            base_field = rel_model._meta.get_field(base_field_name)
                            nested_model = base_field.remote_field.model  # type: ignore[attr-defined]
                            nested_obj = nested_model.objects.filter(**{nested_lookup: val}).first()
                            if not nested_obj:
                                nested_obj = nested_model.objects.create(**{nested_lookup: val})
                            create_kwargs[base_field_name] = nested_obj
                        # Apply per-relation overrides when creating missing related
                        if relation_override_fields and root_field in relation_override_fields:
                            try:
                                create_kwargs.update(relation_override_fields[root_field])
                            except Exception:
                                pass
                        rel_instance = rel_model.objects.create(**create_kwargs)
                    assignments[root_field] = rel_instance
                # Apply any per-row overrides (e.g., force status='open')
                if override_fields:
                    assignments.update(override_fields)
                instances.append(Model(**assignments))
            except Exception:
                errors += 1
                continue

        if not instances:
            return ImportResult(total=total, created=created, updated=updated, skipped=skipped, errors=errors)

        # Determine update_fields for upsert: all assigned top-level fields
        update_fields_set = set()
        for a, _ in parsed:
            for k in a.keys():
                update_fields_set.add(k)
        update_fields = sorted(update_fields_set - set(unique_fields_tuple)) if unique_fields_tuple else sorted(update_fields_set)

        # Perform bulk_create with upsert on conflicts when possible
        if unique_fields_tuple:
            if update_fields:
                res = Model.objects.bulk_create(
                    instances,
                    batch_size=chunk_size,
                    update_conflicts=True,
                    unique_fields=list(unique_fields_tuple),
                    update_fields=update_fields,
                )
            else:
                # Nothing to update on conflict; just ignore duplicates
                res = Model.objects.bulk_create(
                    instances,
                    batch_size=chunk_size,
                    ignore_conflicts=True,
                )
        else:
            res = Model.objects.bulk_create(instances, batch_size=chunk_size)

        # We cannot precisely distinguish created vs updated from bulk_create return across all Django versions.
        # Report all as created for simplicity, since values are persisted regardless.
        created += len(res)
        return ImportResult(total=total, created=created, updated=updated, skipped=skipped, errors=errors)

    elif method == "save_per_instance":
        # Save each row individually to trigger model save() and signals
        with transaction.atomic():
            for assignments, rel_constraints in parsed:
                try:
                    # Resolve relations
                    for root_field, constraints in rel_constraints.items():
                        fobj = field_map.get(root_field)
                        rel_model = fobj.remote_field.model  # type: ignore[attr-defined]
                        constraints = _sanitize_rel_constraints(rel_model, constraints)
                        rel_instance = rel_model.objects.filter(**constraints).first()
                        if not rel_instance:
                            create_kwargs: Dict[str, Any] = {}
                            for key, val in constraints.items():
                                if "__" not in key or key == "pk":
                                    field_name = key if key != "pk" else rel_model._meta.pk.name
                                    create_kwargs[field_name] = val
                                    continue
                                parts_path = key.split("__")
                                base_field_name = parts_path[0]
                                nested_lookup = "__".join(parts_path[1:])
                                base_field = rel_model._meta.get_field(base_field_name)
                                nested_model = base_field.remote_field.model  # type: ignore[attr-defined]
                                nested_obj = nested_model.objects.filter(**{nested_lookup: val}).first()
                                if not nested_obj:
                                    nested_obj = nested_model.objects.create(**{nested_lookup: val})
                                create_kwargs[base_field_name] = nested_obj
                            # Apply per-relation overrides when creating missing related
                            if relation_override_fields and root_field in relation_override_fields:
                                try:
                                    create_kwargs.update(relation_override_fields[root_field])
                                except Exception:
                                    pass
                            rel_instance = rel_model.objects.create(**create_kwargs)
                        assignments[root_field] = rel_instance

                    # Apply any per-row overrides (e.g., force status='open')
                    if override_fields:
                        assignments.update(override_fields)

                    instance = None
                    if unique_fields_tuple:
                        if all((f in assignments) for f in unique_fields_tuple):
                            lookup = {f: assignments[f] for f in unique_fields_tuple}
                            instance = Model.objects.filter(**lookup).first()

                    if instance:
                        changed: List[str] = []
                        for name, value in assignments.items():
                            if getattr(instance, name) != value:
                                setattr(instance, name, value)
                                changed.append(name)
                        # Determine which computed fields to persist
                        recalc_fields: List[str] = []
                        if recalc is not None:
                            if isinstance(recalc, str):
                                if recalc == "all":
                                    try:
                                        recalc_fields = list(getattr(instance, "AUTO_COMPUTE", {}).keys())
                                    except Exception:
                                        recalc_fields = []
                                elif recalc == "none":
                                    recalc_fields = []
                                else:
                                    recalc_fields = [recalc]
                            else:
                                try:
                                    recalc_fields = list(recalc)
                                except Exception:
                                    recalc_fields = []

                        if changed:
                            save_kwargs: Dict[str, Any] = {}
                            if recalc is not None:
                                save_kwargs["recalc"] = recalc
                            if recalc_exclude:
                                save_kwargs["recalc_exclude"] = set(recalc_exclude)
                            # Ensure computed fields are persisted too
                            update_list = list(dict.fromkeys(list(changed) + recalc_fields)) if recalc_fields else changed
                            instance.save(update_fields=update_list, **save_kwargs)
                            updated += 1
                        else:
                            if recalc and recalc_always_save:
                                save_kwargs = {"recalc": recalc}
                                if recalc_exclude:
                                    save_kwargs["recalc_exclude"] = set(recalc_exclude)
                                # Persist only computed fields
                                update_list = recalc_fields
                                if not update_list:
                                    try:
                                        update_list = list(getattr(instance, "AUTO_COMPUTE", {}).keys())
                                    except Exception:
                                        update_list = []
                                if update_list:
                                    instance.save(update_fields=update_list, **save_kwargs)
                                    updated += 1
                                else:
                                    skipped += 1
                            else:
                                skipped += 1
                    else:
                        instance = Model(**assignments)
                        save_kwargs = {}
                        if recalc is not None:
                            save_kwargs["recalc"] = recalc
                        if recalc_exclude:
                            save_kwargs["recalc_exclude"] = set(recalc_exclude)
                        instance.save(**save_kwargs)
                        created += 1
                except Exception:
                    errors += 1
                    continue

        return ImportResult(total=total, created=created, updated=updated, skipped=skipped, errors=errors)

    else:
        raise ValueError("method must be 'bulk_create' or 'save_per_instance'")
