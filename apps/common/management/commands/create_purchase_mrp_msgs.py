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
    help = "Update Purchase MRP Messages"

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Purchase-Orders-"
            else:
                prefix = "C:/inetpub/wwwroot/reports/Purchase-Orders-"

            # Source columns example:
            # Order | Pos | Sq | PN | Description | Order.Date | Pl.Del.Dte | Conf.Date | Modify Dt | Whs | Cur | Ord. | Un.Price | Tot.Amnt | Buyer | Notes on P.O.Line | Itm Gr | Exception Msg | Res.Dt | Suppli

            file_copy = files_utils.read_text_contents(prefix, ["Order", "-"])
            try:
                result = import_rows_from_text(
                    model="common.PurchaseMrpMessage",
                    file_path=file_copy,
                    delimiter="|",
                    has_header=False,
                    ignore_prefixes=[],  # already cleaned in the copy
                    mapping={
                        "0": "pol__order__order",      # PO number
                        "1": "pol__line",              # PO line (Pos)
                        "2": "pol__sequence",          # PO sequence (Sq)
                        "17": "mrp_message",           # Exception Msg
                        "18": "mrp_reschedule_date",   # Res.Dt
                    },
                    method="save_per_instance",  # compute delta/direction/classification on save
                    unique_fields=("pol",),       # OneToOne(pol) implies unique
                    recalc={"reschedule_delta_days", "direction", "classification"},
                    recalc_always_save=True,
                )
                debug_logger.info(
                    "PurchaseMrpMessages import: total=%s created=%s updated=%s skipped=%s errors=%s",
                    result.total, result.created, result.updated, result.skipped, result.errors,
                )
            finally:
                try:
                    os.remove(file_copy)
                except Exception:
                    pass

            debug_logger.info("Updated Purchase MRP Messages via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)
