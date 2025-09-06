import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction


logger = logging.getLogger(__name__)


def _setup_logger(log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger("import_excel")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    # Console handler
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    # File handler
    path = log_file
    if not path:
        os.makedirs("logs", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("logs", f"import_excel_{ts}.log")
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info("Logging to %s", path)
    return logger


def _is_null(value: Any) -> bool:
    # Pandas may pass NaN; also handle empty strings
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
        if s == "":
            return True
        if s.lower() in {"nan", "none", "null"}:
            return True
    return False


def _get_unique_constraints(model: models.Model) -> List[Tuple[str, ...]]:
    opts = model._meta
    uniques: List[Tuple[str, ...]] = []
    # unique_together (legacy)
    for ut in (getattr(opts, "unique_together", None) or []):
        if isinstance(ut, (list, tuple)):
            uniques.append(tuple(ut))
    # UniqueConstraint in Meta.constraints
    for c in getattr(opts, "constraints", []) or []:
        try:
            from django.db.models import UniqueConstraint
            if isinstance(c, UniqueConstraint):
                uniques.append(tuple(c.fields or ()))
        except Exception:
            continue
    # Single unique fields
    for f in opts.fields:
        if getattr(f, "unique", False):
            uniques.append((f.name,))
    # De-dup while preserving order
    seen = set()
    out = []
    for u in uniques:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _coerce_value_for_field(field: models.Field, value: Any) -> Any:
    """Best-effort coercion of raw Excel values to model field types.
    Keeps behavior conservative; only handles common cases like Date/DateTime.
    """
    try:
        from datetime import datetime, date
        # DateField: accept strings like 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' or ISO with 'T'
        if isinstance(field, models.DateField) and not isinstance(field, models.DateTimeField):
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                s = value.strip()
                # Trim time component if present
                if ' ' in s:
                    s = s.split(' ')[0]
                if 'T' in s:
                    s = s.split('T')[0]
                # Try a couple of common formats
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        pass
                return s  # leave as-is; DB/back-end may accept
        # DateTimeField: accept 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS'
        if isinstance(field, models.DateTimeField):
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            if isinstance(value, str):
                s = value.strip()
                # Try ISO first
                try:
                    return datetime.fromisoformat(s)
                except Exception:
                    pass
                # Try common formats
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y'):
                    try:
                        dt = datetime.strptime(s, fmt)
                        if fmt == '%Y-%m-%d' or fmt == '%m/%d/%Y':
                            # Promote date to midnight datetime
                            return datetime.combine(dt.date(), datetime.min.time())
                        return dt
                    except Exception:
                        pass
                return s
    except Exception:
        return value
    return value


class Command(BaseCommand):
    help = "Import an Excel file into a Django model, creating/updating rows based on unique constraints."

    def add_arguments(self, parser):
        parser.add_argument("--excel", required=True, help="Path to Excel .xlsx file")
        parser.add_argument("--model", required=True, help="Target model as 'app_label.ModelName'")
        parser.add_argument("--mapping", help="JSON mapping of Excel column -> model field path (e.g. '{\"Item Code\":\"item__code\"}')")
        parser.add_argument("--mapping-file", help="Path to JSON file with the mapping dictionary")
        parser.add_argument("--sheet", help="Optional sheet name or index (defaults to first)")
        parser.add_argument("--log-file", help="Optional path to log file")

    def handle(self, *args, **options):
        log = _setup_logger(options.get("--log-file") or options.get("log_file"))
        excel_path = options["excel"]
        model_label = options["model"]
        sheet = options.get("sheet")
        # Mapping
        mapping_raw = options.get("mapping")
        mapping_file = options.get("mapping_file")
        if mapping_file:
            try:
                with open(mapping_file, "r", encoding="utf-8") as fh:
                    mapping = json.load(fh)
            except Exception as exc:
                raise CommandError(f"Failed to read mapping file: {exc}")
        elif mapping_raw:
            try:
                mapping = json.loads(mapping_raw)
            except Exception as exc:
                raise CommandError(f"Invalid --mapping JSON: {exc}")
        else:
            raise CommandError("Provide --mapping or --mapping-file")

        if not isinstance(mapping, dict) or not mapping:
            raise CommandError("Mapping must be a non-empty JSON object: {excel_col: 'field' or 'rel__field'}")

        try:
            app_label, model_name = model_label.split(".")
            Model = django_apps.get_model(app_label, model_name)
        except Exception as exc:
            raise CommandError(f"Invalid model label '{model_label}': {exc}")

        unique_sets = _get_unique_constraints(Model)
        if not unique_sets:
            log.warning("No unique constraints found for %s; all rows will be created (no upserts)", Model)

        # Read Excel
        try:
            # Read all cells as strings to preserve leading zeros from Excel
            # and avoid numeric coercion that would strip formatting.
            df = pd.read_excel(
                excel_path,
                sheet_name=(sheet if sheet else 0),
                dtype=str,
                keep_default_na=False,
            )
        except Exception as exc:
            raise CommandError(f"Failed to read Excel: {exc}")

        # Normalize column names to strings
        df.columns = [str(c) for c in df.columns]

        total = len(df)
        created = 0
        updated = 0
        errors = 0

        # Pre-resolve field objects for top-level assignments
        field_map: Dict[str, models.Field] = {f.name: f for f in Model._meta.get_fields() if hasattr(f, 'attname')}

        for idx, row in df.iterrows():
            row_no = idx + 2  # considering Excel headers on row 1
            try:
                # Prepare collected values and related instances
                assignments: Dict[str, Any] = {}

                # Resolve mapping per column
                for excel_col, path in mapping.items():
                    if excel_col not in df.columns:
                        log.warning("Row %s: column '%s' not in sheet; skipping this mapping", row_no, excel_col)
                        continue
                    raw_value = row[excel_col]
                    if _is_null(raw_value):
                        continue
                    if "__" in path:
                        # Resolve relation chain and set FK on the root model
                        root_field, *subpath = path.split("__")
                        fobj = field_map.get(root_field)
                        if not fobj or not (hasattr(fobj, 'remote_field') and fobj.remote_field):
                            raise ValueError(f"Mapping points to relation '{root_field}' which is not a ForeignKey/OneToOne")
                        rel_model = fobj.remote_field.model
                        # Build lookup on the related model from the remaining path and raw_value
                        if not subpath:
                            # Direct FK value (assume PK provided)
                            rel_instance = rel_model.objects.filter(pk=raw_value).first()
                            if not rel_instance:
                                # Attempt creation by assigning PK directly if allowed
                                try:
                                    rel_instance = rel_model.objects.create(pk=raw_value)
                                except Exception:
                                    raise ValueError(f"Related {rel_model.__name__} with pk={raw_value} not found and could not be created.")
                        else:
                            lookup_field = "__".join(subpath)
                            # Only support single-field equality lookups on related for now
                            rel_qs = rel_model.objects.filter(**{lookup_field: raw_value})
                            rel_instance = rel_qs.first()
                            if not rel_instance:
                                # Try to create minimal related row
                                try:
                                    create_kwargs = {lookup_field: raw_value}
                                    # If creating a user-like model that requires a username,
                                    # use the same value as a sensible default when not provided.
                                    rel_field_names = {f.name for f in rel_model._meta.get_fields() if hasattr(f, 'attname')}
                                    if 'username' in rel_field_names and 'username' not in create_kwargs:
                                        create_kwargs['username'] = str(raw_value)
                                    rel_instance = rel_model.objects.create(**create_kwargs)
                                except Exception as exc:
                                    raise ValueError(
                                        f"Related {rel_model.__name__} lookup {lookup_field}={raw_value!r} not found and could not be created: {exc}"
                                    )
                        assignments[root_field] = rel_instance
                    else:
                        # Coerce value types for concrete fields (e.g., DateField)
                        fobj = field_map.get(path)
                        if fobj is not None:
                            raw_value = _coerce_value_for_field(fobj, raw_value)
                        assignments[path] = raw_value

                # Determine existing row via unique constraints
                instance = None
                for fields in unique_sets:
                    # Only try constraints we can fully satisfy from assignments
                    if all((f in assignments) for f in fields):
                        lookup = {f: assignments[f] for f in fields}
                        try:
                            instance = Model.objects.filter(**lookup).first()
                        except Exception:
                            instance = None
                        if instance:
                            break

                with transaction.atomic():
                    if instance:
                        # Update
                        for name, value in assignments.items():
                            setattr(instance, name, value)
                        instance.save()
                        updated += 1
                    else:
                        # Create
                        instance = Model(**assignments)
                        instance.save()
                        created += 1

            except Exception as exc:
                errors += 1
                log.error("Row %s: %s", row_no, exc, exc_info=False)

        log.info("Done. Total: %s, created: %s, updated: %s, errors: %s", total, created, updated, errors)
        if errors:
            raise CommandError(f"Completed with {errors} errors; see log for details.")
