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
    help = "Update Planned Purchase Orders"

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Planned-PO-"
            else:
                prefix = "/srv/mag360mai/reports/Planned-PO-"

            # Source columns example:
            # Order | Order Item | Order Quantity | Pl.St.Dt | Pl.Fi.Dt | Req.Date | Buyer | supplier | Shop Floor Pln

            file_copy = files_utils.read_text_contents(prefix, ["Date", "MAI", "ELIMETAL", "Order", "|", "-"])
            try:
                result = import_rows_from_text(
                    model="common.PlannedPurchaseOrder",
                    file_path=file_copy,
                    delimiter="|",
                    has_header=False,
                    ignore_prefixes=[],  # already cleaned in the copy
                    mapping={
                        "0": "order",
                        "1": "item__code",
                        "2": "quantity",
                        "3": "planned_start_date",
                        "4": "planned_end_date",
                        "5": "required_date",
                        "6": "buyer__username",
                        "7": "supplier__code",
                    },
                    method="bulk_create",
                )
                debug_logger.info(
                    "PlannedPurchaseOrders import: total=%s created=%s updated=%s skipped=%s errors=%s",
                    result.total, result.created, result.updated, result.skipped, result.errors,
                )
            finally:
                try:
                    os.remove(file_copy)
                except Exception:
                    pass

            debug_logger.info("Updated Planned Purchase Orders via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)

