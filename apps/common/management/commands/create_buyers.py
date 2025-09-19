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
    help = "Import Buyers into accounts.CustomUser"

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                prefix = "C:/Users/n.mantha/Desktop/datafiles/Buyers-"
            else:
                prefix = "C:/inetpub/wwwroot/reports/Buyers-"

            file_copy = files_utils.read_text_contents(prefix, ["Date", "MAI - ", "ELIMETAL - ", "Employee", "|", "-"])
            try:
                result = import_rows_from_text(
                    model="accounts.CustomUser",
                    file_path=file_copy,
                    delimiter="|",
                    has_header=False,
                    ignore_prefixes=[],  # already cleaned in the copy
                    # Text file columns: Employee | Name | Given Name
                    # Mapping requested: Employee -> username, Name -> first_name
                    mapping={
                        "0": "username",     # Employee
                        "1": "first_name",   # Name
                        # "2": "last_name",  # Given Name (left unmapped unless needed)
                    },
                    method="bulk_create",
                    unique_fields=("username",),
                )
                debug_logger.info(
                    "CustomUsers import: total=%s created=%s updated=%s skipped=%s errors=%s",
                    result.total, result.created, result.updated, result.skipped, result.errors,
                )
            finally:
                try:
                    os.remove(file_copy)
                except Exception:
                    pass

            debug_logger.info("Updated Custom Users via importer")

        except Exception as e:
            error_logger.error(e, exc_info=True)
