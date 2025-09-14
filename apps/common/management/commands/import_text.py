import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from apps.common.functions import files as files_utils


def _setup_logger(log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger("import_text")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    path = log_file
    if not path:
        os.makedirs("logs", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("logs", f"import_text_{ts}.log")
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info("Logging to %s", path)
    return logger


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


def _get_unique_constraints(model: models.Model) -> List[Tuple[str, ...]]:
    opts = model._meta
    uniques: List[Tuple[str, ...]] = []
    for ut in (getattr(opts, "unique_together", None) or []):
        if isinstance(ut, (list, tuple)):
            uniques.append(tuple(ut))
    for c in getattr(opts, "constraints", []) or []:
        try:
            from django.db.models import UniqueConstraint
            if isinstance(c, UniqueConstraint):
                uniques.append(tuple(c.fields or ()))
        except Exception:
            continue
    for f in opts.fields:
        if getattr(f, "unique", False):
            uniques.append((f.name,))
    seen = set()
    out = []
    for u in uniques:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


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


class Command(BaseCommand):
    help = "Import a delimited text file into a Django model with optional cleaning and upsert support."

    def add_arguments(self, parser):
        src = parser.add_mutually_exclusive_group(required=True)
        src.add_argument("--file", help="Path to the input text file")
        src.add_argument(
            "--prefix",
            help=(
                "Base path prefix for date-stamped files (e.g. '.../Purchase-Orders-BP-'). "
                "Importer will locate the most recent file up to 10 days back."
            ),
        )

        parser.add_argument("--model", required=True, help="Target model as 'app_label.ModelName'")
        parser.add_argument("--delimiter", default="|", help="Field delimiter (default: '|')")
        parser.add_argument("--has-header", action="store_true", help="Treat first row as header names")
        parser.add_argument(
            "--mapping",
            required=True,
            help=(
                "JSON mapping of column -> model field path. "
                "If --has-header, keys are header names; otherwise keys are zero-based indices as strings."
            ),
        )
        parser.add_argument(
            "--value-map",
            help="JSON mapping of column key (header or index str) -> {from_value: to_value} for pre-assignment transforms",
        )
        parser.add_argument(
            "--ignore-prefix",
            action="append",
            default=[],
            help="Line prefixes to ignore during cleaning (can be provided multiple times)",
        )
        parser.add_argument("--log-file", help="Optional path to log file")
        parser.add_argument("--dry-run", action="store_true", help="Parse and validate without saving")
        parser.add_argument("--limit", type=int, help="Limit number of data rows to process")
        # Auto-compute policy passthrough (for AutoComputeMixin models)
        parser.add_argument(
            "--recalc",
            choices=["all", "none"],
            help="Auto-computation policy: compute all or none (default: all)",
        )
        parser.add_argument(
            "--recalc-exclude",
            action="append",
            default=[],
            help="Auto-computed fields to exclude (can be provided multiple times)",
        )

    def handle(self, *args, **options):
        log = _setup_logger(options.get("log_file"))

        delimiter: str = options["delimiter"]
        has_header: bool = options["has_header"]
        mapping_raw: str = options["mapping"]
        value_map_raw: Optional[str] = options.get("value_map")
        ignore_prefixes: List[str] = options.get("ignore_prefix") or []
        dry_run: bool = options.get("dry_run", False)
        limit: Optional[int] = options.get("limit")
        recalc = options.get("recalc")
        recalc_exclude: Iterable[str] = options.get("recalc_exclude") or []

        # Resolve model
        try:
            app_label, model_name = options["model"].split(".")
            Model = django_apps.get_model(app_label, model_name)
        except Exception as exc:
            raise CommandError(f"Invalid model label '{options['model']}': {exc}")

        # Mapping
        try:
            mapping = json.loads(mapping_raw)
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError("Mapping must be a non-empty JSON object")
        except Exception as exc:
            raise CommandError(f"Invalid --mapping JSON: {exc}")

        # Value transforms
        value_map: Dict[str, Dict[Any, Any]] = {}
        if value_map_raw:
            try:
                vm = json.loads(value_map_raw)
                if isinstance(vm, dict):
                    value_map = vm
            except Exception as exc:
                raise CommandError(f"Invalid --value-map JSON: {exc}")

        # Choose source file and optionally clean it like existing utilities
        file_path: Optional[str] = None
        cleanup_copy = False
        if options.get("prefix"):
            try:
                file_path = files_utils.read_text_contents(options["prefix"], ignore_prefixes)
            except Exception as exc:
                raise CommandError(f"Could not resolve prefix to a file: prefix='{options['prefix']}', error={exc}")
            cleanup_copy = True
        else:
            file_path = options["file"]
            if not os.path.exists(file_path):
                raise CommandError(f"File not found: {file_path}")
            # If ignore prefixes were provided for a direct file, mimic cleaning by creating a copy
            if ignore_prefixes:
                file_path = files_utils.read_text_contents(file_path.replace(".txt", ""), ignore_prefixes)
                cleanup_copy = True

        log.info("Using file: %s", file_path)

        # Read rows
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                raw_lines = [ln.rstrip("\n\r") for ln in fh.readlines()]
        except Exception as exc:
            raise CommandError(f"Failed to read file: {exc}")
        finally:
            # remove the temp copy produced by read_text_contents
            if cleanup_copy:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

        header: List[str] = []
        data_lines: List[str] = []
        if has_header and raw_lines:
            header = [h.strip() for h in raw_lines[0].split(delimiter)]
            data_lines = raw_lines[1:]
        else:
            data_lines = raw_lines

        log.info(
            "Parsed file: raw_lines=%s, header=%s, data_lines=%s, delimiter='%s'",
            len(raw_lines), bool(header), len(data_lines), delimiter,
        )
        if has_header and header:
            log.info("Header columns: %s", header)

        # Compute unique constraints for upsert
        unique_sets = _get_unique_constraints(Model)
        if not unique_sets:
            log.warning("No unique constraints found for %s; all rows will be created (no upserts)", Model)

        # Field metadata
        field_map: Dict[str, models.Field] = {f.name: f for f in Model._meta.get_fields() if hasattr(f, 'attname')}

        total = 0
        created = 0
        updated = 0
        errors = 0
        skipped = 0

        for idx, line in enumerate(data_lines):
            if limit and total >= limit:
                break
            total += 1

            # Skip commented lines per existing utility
            if not files_utils.check_file_line(line):
                skipped += 1
                continue

            try:
                parts = [p.strip() for p in line.split(delimiter)]
                # Build assignments
                assignments: Dict[str, Any] = {}
                rel_constraints: Dict[str, Dict[str, Any]] = {}

                for key, path in mapping.items():
                    # Determine value by header name or index
                    if has_header and not str(key).isdigit():
                        if not header:
                            raise ValueError("--has-header specified but header not parsed")
                        try:
                            col_index = header.index(str(key))
                        except ValueError:
                            continue  # header not present; skip mapping
                    else:
                        try:
                            col_index = int(key)
                        except Exception:
                            # key isn't an int index and we don't have header mapping; skip
                            continue

                    if col_index < 0 or col_index >= len(parts):
                        continue
                    raw_value: Any = parts[col_index]

                    # Apply value transform per column key
                    try:
                        col_map = value_map.get(str(key)) if isinstance(value_map, dict) else None
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

                # Resolve relations
                for root_field, constraints in rel_constraints.items():
                    fobj = field_map.get(root_field)
                    rel_model = fobj.remote_field.model  # type: ignore[attr-defined]
                    try:
                        rel_instance = rel_model.objects.filter(**constraints).first()
                    except Exception:
                        rel_instance = None
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
                        rel_instance = rel_model.objects.create(**create_kwargs)
                    assignments[root_field] = rel_instance

                # Upsert by unique constraints
                instance = None
                for fields in unique_sets:
                    if all((f in assignments) for f in fields):
                        lookup = {f: assignments[f] for f in fields}
                        instance = Model.objects.filter(**lookup).first()
                        if instance:
                            break

                if dry_run:
                    # Just validate mapping and relation resolution; no DB writes
                    continue

                with transaction.atomic():
                    if instance:
                        for name, value in assignments.items():
                            setattr(instance, name, value)
                        save_kwargs = {}
                        if recalc is not None:
                            save_kwargs["recalc"] = recalc
                        if recalc_exclude:
                            save_kwargs["recalc_exclude"] = set(recalc_exclude)
                        instance.save(**save_kwargs)
                        updated += 1
                    else:
                        instance = Model(**assignments)
                        save_kwargs = {}
                        if recalc is not None:
                            save_kwargs["recalc"] = recalc
                        if recalc_exclude:
                            save_kwargs["recalc_exclude"] = set(recalc_exclude)
                        instance.save(**save_kwargs)
                        created += 1

            except Exception as exc:
                errors += 1
                # Row number accounting for header if present
                row_no = idx + 1 + (1 if has_header else 0)
                log.error("Row %s: %s", row_no, exc, exc_info=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Total: {total}, created: {created}, updated: {updated}, errors: {errors}"
            )
        )
        log.info(
            "Done. Total=%s, created=%s, updated=%s, errors=%s, skipped=%s",
            total, created, updated, errors, skipped,
        )
        if errors:
            raise CommandError(f"Completed with {errors} errors; see log for details.")
