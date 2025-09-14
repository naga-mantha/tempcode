from django.core.management.base import BaseCommand
from apps.common.models import (
    PurchaseMrpMessage,
    PurchaseOrder,
    PurchaseOrderLine,
)
from apps.common.functions import files
import os
import environ
import re
import logging
from datetime import date, datetime

env = environ.Env()
environ.Env.read_env()
status = env('STATUS')
error_logger = logging.getLogger(name="app_errors")
debug_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update MRP Messages'

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                file = "C:/Users/n.mantha/Desktop/datafiles/Purchase-Orders-"
            else:
                file = "C:/inetpub/wwwroot/reports/Tasks-"
            file_copy = files.read_text_contents(file, ["Order", "-"])
            created_count = 0

            # Open the copied file and read the contents
            with open(file_copy, "r") as f:
                lines = f.readlines()

            for line in lines:
                line_check = files.check_file_line(line)

                if line_check == False:
                    error_logger.error("Line Error ##: %s" % (line))

                else:
                    currentline = line.split("|")

                    mrp_message = currentline[17].strip()
                    if mrp_message:
                        try:
                            purchase_order = PurchaseOrder.objects.get_or_create(order=currentline[0].strip())[0]
                            purchase_order_line = int(currentline[1].strip()) if currentline[1].strip() else None
                            sequence = int(currentline[2].strip()) if currentline[2].strip() else None

                            pol, _ = PurchaseOrderLine.objects.get_or_create(
                                order=purchase_order,
                                line=purchase_order_line,
                                sequence=sequence,
                            )

                            # Build the message instance for Purchase order lines
                            obj = PurchaseMrpMessage(
                                pol=pol,
                                mrp_message=mrp_message,
                            )

                            # Parse date (column 18) as a date, not datetime
                            raw_date = currentline[18].strip() if len(currentline) > 18 else ""
                            if raw_date:
                                try:
                                    obj.mrp_reschedule_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
                                except ValueError:
                                    # Log and skip assigning date if format is unexpected
                                    error_logger.error("Invalid date format '%s' in line: %s", raw_date, line)
                                    obj.mrp_reschedule_date = None
                            else:
                                obj.mrp_reschedule_date = None

                            # Save individually to trigger MrpMessage.save() hooks (delta/direction)
                            obj.save()
                            created_count += 1
                        except Exception as line_exc:
                            error_logger.error("Failed to process line: %s", line, exc_info=True)

            os.remove(file_copy)

            debug_logger.info("Created %s MRP messages from text import", created_count)

        except Exception as e:
            error_logger.error(e, exc_info=True)
