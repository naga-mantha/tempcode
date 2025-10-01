import logging
import os
import environ
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.common.models import PurchaseOrderLine
from apps.common.functions import files as files_utils
from apps.common.importers.text import import_rows_from_text


env = environ.Env()
environ.Env.read_env()
status = env("STATUS")
error_logger = logging.getLogger(name="app_errors")
debug_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update Purchase Order Lines"

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Purchase-Orders-BP-"
            else:
                prefix = "/srv/mag360mai/reports/Purchase-Orders-BP-"

            # Create a cleaned copy of the latest date-stamped file
            file_copy = files_utils.read_text_contents(prefix, ["Order", "-"])
            try:
                with transaction.atomic():
                    # Close all lines first
                    closed = PurchaseOrderLine.objects.exclude(status="closed").update(status="closed")
                    debug_logger.info("Closed existing PurchaseOrderLines: %s", closed)

                    # Import snapshot; force status='open' for present rows, compute only final_receive_date
                    result = import_rows_from_text(
                        model="common.PurchaseOrderLine",
                        file_path=file_copy,
                        delimiter="|",
                        has_header=False,
                        ignore_prefixes=[],  # already cleaned in the copy
                        mapping={
                            "0": "order__order",
                            "1": "line",
                            "2": "sequence",
                            "4": "item__code",
                            "6": "order_date",
                            "7": "initial_receive_date",
                            "8": "supplier_confirmed_date",
                            "9": "modified_receive_date",
                            "14": "total_quantity",
                            "15": "received_quantity",
                            "16": "back_order",
                            "17": "unit_price",
                            "11": "currency__code",
                            "18": "amount_original_currency",
                            "21": "comments",
                        },
                        method="save_per_instance",
                        unique_fields=("order", "line", "sequence"),
                        recalc={"final_receive_date", "amount_home_currency"},
                        recalc_always_save=True,
                        override_fields={"status": "open"},
                    )
                    debug_logger.info(
                        "PurchaseOrderLines import: total=%s created=%s updated=%s skipped=%s errors=%s",
                        result.total, result.created, result.updated, result.skipped, result.errors,
                    )
            finally:
                try:
                    os.remove(file_copy)
                except Exception:
                    pass

            debug_logger.info("Updated Purchase Order Lines via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)
