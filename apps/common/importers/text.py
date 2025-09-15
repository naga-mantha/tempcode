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


# Streaming implementation to handle large files in batches while preserving the same API.
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

    # Prepare model field map
    field_map: Dict[str, models.Field] = {f.name: f for f in Model._meta.get_fields() if hasattr(f, "attname")}

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

    # Helpers
    def _col_index_for(headers: List[str]):
        def _inner(key: Union[str, int]) -> Optional[int]:
            if has_header and not str(key).isdigit():
                try:
                    return headers.index(str(key))
                except ValueError:
                    return None
            try:
                return int(key)
            except Exception:
                return None
        return _inner

    def _sanitize_rel_constraints(rel_model: models.Model, constraints: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, val in constraints.items():
            if isinstance(val, str):
                val = val.strip()
            try:
                if rel_model.__name__ == "Currency":
                    field_name = key.split("__", 1)[0] if key else "code"
                    if field_name == "code" and isinstance(val, str):
                        max_len = getattr(rel_model._meta.get_field("code"), "max_length", 5)
                        val = val.upper()[: max_len or 5]
            except Exception:
                pass
            out[key] = val
        return out

    def _parse_line(parts: List[str], col_index) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        assignments: Dict[str, Any] = {}
        rel_constraints: Dict[str, Dict[str, Any]] = {}
        for key, path in mapping.items():
            idx = col_index(key)
            if idx is None or idx >= len(parts):
                raw_value = None
            else:
                raw_value = parts[idx]
            # Normalize blank strings to None and trim whitespace
            if isinstance(raw_value, str):
                rv = raw_value.strip()
                if rv == "" or rv.lower() in {"nan", "none", "null"}:
                    raw_value = None
                else:
                    raw_value = rv
            if key in value_map:
                try:
                    raw_value = value_map[key].get(raw_value, raw_value)
                except Exception:
                    pass
            if "__" in path:
                root_field, lookup = path.split("__", 1)
                cons = rel_constraints.setdefault(root_field, {})
                cons[lookup] = raw_value
            else:
                fobj = field_map.get(path)
                if fobj is not None:
                    raw_value = _coerce_value_for_field(fobj, raw_value)
                assignments[path] = raw_value
        return assignments, rel_constraints

    method = (method or "bulk_create").lower()

    total = 0
    created = 0
    updated = 0
    skipped = 0
    errors = 0
    seen_keys: set = set()

    # Open the file in streaming mode
    enc = encoding or "utf-8"
    errs = encoding_errors if encoding else "replace"
    with open(file_path, "r", encoding=enc, errors=errs) as fh:
        header_cols: List[str] = []
        if has_header:
            first = fh.readline()
            if first:
                header_cols = [h.strip() for h in first.rstrip("\n\r").split(delimiter)]
        col_index = _col_index_for(header_cols)

        batch_lines: List[str] = []

        def process_batch(lines: List[str]):
            nonlocal total, created, updated, skipped, errors
            if not lines:
                return
            # Parse lines to assignments/constraints
            parsed_batch: List[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]] = []
            for ln in lines:
                total += 1
                try:
                    parts = [p.strip() for p in ln.split(delimiter)]
                    assignments, rel_constraints = _parse_line(parts, col_index)

                    # Duplicate detection across entire stream
                    if unique_fields_tuple:
                        identity_values: List[Any] = []
                        for f in unique_fields_tuple:
                            if f in assignments:
                                identity_values.append(assignments.get(f))
                            elif f in rel_constraints:
                                cons = rel_constraints[f]
                                if "pk" in cons:
                                    identity_values.append(cons["pk"])
                                elif len(cons) == 1:
                                    identity_values.append(next(iter(cons.values())))
                                else:
                                    identity_values.append(tuple(sorted(cons.items())))
                            else:
                                identity_values.append(None)
                        key_tuple = tuple(identity_values)
                        if key_tuple in seen_keys:
                            msg = f"Duplicate input row detected for unique key {unique_fields_tuple}={key_tuple!r}"
                            if stop_on_duplicate:
                                raise ValueError(msg)
                            else:
                                skipped += 1
                                continue
                        seen_keys.add(key_tuple)

                    parsed_batch.append((assignments, rel_constraints))
                except Exception:
                    errors += 1
                    continue

            if dry_run or not parsed_batch:
                return

            if method == "bulk_create":
                # Resolve relations and build instances
                instances: List[models.Model] = []
                update_fields_set = set()
                for assignments, rel_constraints in parsed_batch:
                    try:
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
                                if relation_override_fields and root_field in relation_override_fields:
                                    try:
                                        create_kwargs.update(relation_override_fields[root_field])
                                    except Exception:
                                        pass
                                rel_instance = rel_model.objects.create(**create_kwargs)
                            assignments[root_field] = rel_instance
                        if override_fields:
                            assignments.update(override_fields)
                        for k in assignments.keys():
                            update_fields_set.add(k)
                        instances.append(Model(**assignments))
                    except Exception:
                        errors += 1
                        continue

                if not instances:
                    return

                update_fields = (
                    sorted(update_fields_set - set(unique_fields_tuple)) if unique_fields_tuple else sorted(update_fields_set)
                )
                if unique_fields_tuple:
                    if update_fields:
                        Model.objects.bulk_create(
                            instances,
                            batch_size=chunk_size,
                            update_conflicts=True,
                            unique_fields=list(unique_fields_tuple),
                            update_fields=update_fields,
                        )
                    else:
                        Model.objects.bulk_create(
                            instances,
                            batch_size=chunk_size,
                            ignore_conflicts=True,
                        )
                else:
                    Model.objects.bulk_create(instances, batch_size=chunk_size)
                created += len(instances)

            elif method == "save_per_instance":
                with transaction.atomic():
                    for assignments, rel_constraints in parsed_batch:
                        try:
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
                                    if relation_override_fields and root_field in relation_override_fields:
                                        try:
                                            create_kwargs.update(relation_override_fields[root_field])
                                        except Exception:
                                            pass
                                    rel_instance = rel_model.objects.create(**create_kwargs)
                                assignments[root_field] = rel_instance

                            if override_fields:
                                assignments.update(override_fields)

                            instance = None
                            if unique_fields_tuple and all((f in assignments) for f in unique_fields_tuple):
                                lookup = {f: assignments[f] for f in unique_fields_tuple}
                                instance = Model.objects.filter(**lookup).first()

                            if instance:
                                changed: List[str] = []
                                for name, value in assignments.items():
                                    if getattr(instance, name) != value:
                                        setattr(instance, name, value)
                                        changed.append(name)

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
                                    update_list = list(dict.fromkeys(list(changed) + recalc_fields)) if recalc_fields else changed
                                    instance.save(update_fields=update_list, **save_kwargs)
                                    updated += 1
                                else:
                                    if recalc and recalc_always_save:
                                        save_kwargs = {"recalc": recalc}
                                        if recalc_exclude:
                                            save_kwargs["recalc_exclude"] = set(recalc_exclude)
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
            else:
                raise ValueError("method must be 'bulk_create' or 'save_per_instance'")

        # Stream lines and process in batches
        for raw in fh:
            ln = raw.rstrip("\n\r")
            if not ln or any(ln.startswith(pfx) for pfx in ignore_prefixes):
                continue
            batch_lines.append(ln)
            if len(batch_lines) >= max(1, int(chunk_size or 1000)):
                process_batch(batch_lines)
                batch_lines = []

        if batch_lines:
            process_batch(batch_lines)

    return ImportResult(total=total, created=created, updated=updated, skipped=skipped, errors=errors)

