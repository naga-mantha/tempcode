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
    help = "Update Receipts"

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Receipts-"
            else:
                prefix = "/srv/mag360mai/reports/Receipts-"

            # Create a cleaned copy of the latest date-stamped file
            file_copy = files_utils.read_text_contents(prefix, ["Date", "Company", "Receipt", "|", "-"])
            try:
                result = import_rows_from_text(
                    model="common.Receipt",
                    file_path=file_copy,
                    delimiter="|",
                    has_header=False,
                    ignore_prefixes=[],  # already cleaned in the copy
                    mapping={
                        "0": "number",
                    },
                    method="bulk_create",
                    unique_fields=("number",),
                )
                debug_logger.info(
                    "Receipts import: total=%s created=%s updated=%s skipped=%s errors=%s",
                    result.total, result.created, result.updated, result.skipped, result.errors,
                )
            finally:
                try:
                    os.remove(file_copy)
                except Exception:
                    pass

            debug_logger.info("Updated Receipts via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)
