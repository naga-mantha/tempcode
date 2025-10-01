import logging
import os
import environ
from django.core.management.base import BaseCommand
from apps.common.functions import files as files_utils
from apps.common.importers.text import import_rows_from_text


env = environ.Env()
environ.Env.read_env()
status = env("STATUS")
error_logger = logging.getLogger(name="app_errors")
debug_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update Items"

    def handle(self, *args, **kwargs):
        file_copy = None
        file_copy_filtered = None
        try:
            # Determine source prefix by environment
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Parts-"
            else:
                prefix = "/srv/mag360mai/reports/Parts-"

            # Create a cleaned copy of the latest date-stamped file
            # Header is: "Item Group | Description | Item | Description | Item Type | tcibd001.srce | Signal"
            file_copy = files_utils.read_text_contents(prefix, ["Date:", "MAI -", "ELIMETAL -", "Item Group", "-",])

            # Further filter rows per business rules before importing
            # 1) Skip if Item starts with "PROG02"
            # 2) Skip if Description is "Do Not Use"
            base = os.path.basename(file_copy)
            file_copy_filtered = os.path.join(os.path.dirname(file_copy) or ".", f"filtered {base}")
            item_group_desc_map = {}
            with open(file_copy, "r", encoding="utf-8") as src, open(file_copy_filtered, "w", encoding="utf-8") as dst:
                for raw in src:
                    line = raw.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) < 4:
                        continue
                    item_code = parts[2]
                    item_desc = parts[3]
                    group_code = parts[0] if len(parts) > 0 else ""
                    group_desc = parts[1] if len(parts) > 1 else ""
                    if item_code.startswith("PROG02"):
                        continue
                    if item_desc.strip().lower() == "do not use":
                        continue
                    # Track latest description for each Item Group code
                    if group_code:
                        item_group_desc_map[group_code] = group_desc
                    dst.write(" | ".join(parts))
                    dst.write("\n")

            # Import using the shared text importer
            try:
                result = import_rows_from_text(
                    model="common.Item",
                    file_path=file_copy_filtered,
                    delimiter="|",
                    has_header=False,
                    ignore_prefixes=[],
                    mapping={
                        "0": "item_group__code",         # Item Group code
                        "2": "code",                     # Item code
                        "3": "description",              # Item description
                        "4": "type__code",               # Item Type code
                    },
                    method="bulk_create",
                    unique_fields=("code",),
                )
                debug_logger.info(
                    "Items import: total=%s created=%s updated=%s skipped=%s errors=%s",
                    result.total, result.created, result.updated, result.skipped, result.errors,
                )
            finally:
                # Clean up filtered copy
                try:
                    if file_copy_filtered and os.path.exists(file_copy_filtered):
                        os.remove(file_copy_filtered)
                except Exception:
                    pass

            # Post-update: align ItemGroup descriptions from the latest file
            try:
                from apps.common.models import ItemGroup
                updated_groups = 0
                for code, desc in item_group_desc_map.items():
                    changed = ItemGroup.objects.filter(code=code).exclude(description=desc).update(description=desc)
                    updated_groups += int(changed or 0)
                if updated_groups:
                    debug_logger.info("ItemGroup descriptions updated: %s", updated_groups)
            except Exception:
                # Non-fatal; continue without blocking the import
                pass

            debug_logger.info("Updated Items via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)
        finally:
            # Clean up original temporary copy
            try:
                if file_copy and os.path.exists(file_copy):
                    os.remove(file_copy)
            except Exception:
                pass
