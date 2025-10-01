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
    help = "Update Receipt Lines"

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Receipts-"
            else:
                prefix = "/srv/mag360mai/reports/Receipts-"

            # Example columns in source:
            # Receipt | Sq | Receipt Dt | Rec, Qty | Order | Pos. | Seq | Item | BP | Prod.Ord | ImpRic (CAD)
            # We import a subset necessary to build ReceiptLine and link to PO Line.

            file_copy = files_utils.read_text_contents(prefix, ["Date", "Company", "Receipt", "|", "-"])
            try:
                result = import_rows_from_text(
                    model="common.ReceiptLine",
                    file_path=file_copy,
                    delimiter="|",
                    has_header=False,
                    ignore_prefixes=[],
                    mapping={
                        "0": "receipt__number",           # Receipt number
                        "1": "line",                     # Receipt line number (Sq)
                        "2": "receipt_date",             # Receipt Dt
                        "3": "received_quantity",        # Rec, Qty
                        "4": "po_line__order__order",    # Order (PO number)
                        "5": "po_line__line",            # Pos. (PO line)
                        "6": "po_line__sequence",        # Seq (PO line sequence)
                        "10": "amount_home_currency",  # ImpRic (CAD)
                        # other columns ignored
                    },
                    method="save_per_instance",  # compute fields via AutoComputeMixin
                    unique_fields=("receipt", "line"),
                    recalc={"days_offset", "classification"},
                    recalc_always_save=True,
                    relation_override_fields={
                        "po_line": {"status": "closed"},
                    },
                )
                debug_logger.info(
                    "ReceiptLines import: total=%s created=%s updated=%s skipped=%s errors=%s",
                    result.total, result.created, result.updated, result.skipped, result.errors,
                )
            finally:
                try:
                    os.remove(file_copy)
                except Exception:
                    pass

            debug_logger.info("Updated Receipt Lines via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)
