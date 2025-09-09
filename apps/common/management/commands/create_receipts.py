from django.core.management.base import BaseCommand
from apps.common.models import *
from apps.common.functions import files
import os
from datetime import date, datetime
import environ
import re
import logging

env = environ.Env()
environ.Env.read_env()
status = env('STATUS')
error_logger = logging.getLogger(name="app_errors")
debug_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update Items'

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                file = "C:/Users/n.mantha/Desktop/datafiles/Receipts-"
            else:
                file = "C:/inetpub/wwwroot/reports/Receipts-"
            file_copy = files.read_text_contents(file, ["Date", "Company", "Receipt", "|", "-"])
            objects_map = {}

            # Open the copied file and read the contents
            with open(file_copy, "r") as f:
                lines = f.readlines()

            for line in lines:
                try:
                    line_check = files.check_file_line(line)
                    if line_check is False:
                        error_logger.error("Line Error ##: %s" % (line.strip()))
                        continue

                    currentline = line.split("|")
                    receipt_no = (currentline[0] or "").strip()
                    line_no_raw = (currentline[1] or "").strip()
                    receipt_dt_raw = (currentline[2] or "").strip()
                    qty_raw = (currentline[3] or "").strip()
                    po_no = (currentline[4] or "").strip()
                    pol_line_raw = (currentline[5] or "").strip()
                    pol_seq_raw = (currentline[6] or "").strip()

                    # Basic required fields validation
                    if not receipt_no or not line_no_raw:
                        error_logger.error("Missing receipt or line ##: %s" % (line.strip()))
                        continue

                    # Parse numerics and date
                    try:
                        line_no = int(line_no_raw)
                    except Exception:
                        error_logger.error("Invalid line number ##: %s" % (line.strip()))
                        continue

                    received_quantity = None
                    if qty_raw != "":
                        try:
                            received_quantity = float(qty_raw)
                        except Exception:
                            error_logger.error("Invalid quantity ##: %s" % (line.strip()))
                            continue

                    receipt_date = None
                    if receipt_dt_raw:
                        try:
                            receipt_date = datetime.strptime(receipt_dt_raw, '%Y-%m-%d').date()
                        except Exception:
                            error_logger.error("Invalid date ##: %s" % (line.strip()))
                            continue

                    # Build related objects; require PO fields for a valid line
                    if not po_no or not pol_line_raw or not pol_seq_raw:
                        error_logger.error("Missing PO reference ##: %s" % (line.strip()))
                        continue

                    try:
                        pol_line = int(pol_line_raw)
                        pol_seq = int(pol_seq_raw)
                    except Exception:
                        error_logger.error("Invalid PO line/sequence ##: %s" % (line.strip()))
                        continue

                    po = PurchaseOrder.objects.get_or_create(order=po_no)[0]
                    rl_receipt = Receipt.objects.get_or_create(number=receipt_no)[0]
                    pol = PurchaseOrderLine.objects.get_or_create(order=po, line=pol_line, sequence=pol_seq)[0]

                    obj = ReceiptLine(
                        receipt=rl_receipt,
                        line=line_no,
                        po_line=pol,
                        received_quantity=received_quantity,
                        receipt_date=receipt_date,
                    )

                    # Compute derived fields now, because bulk_create does not call save()
                    obj.days_offset = obj.compute_days_offset()
                    obj.amount_home_currency = obj.compute_amount_home_currency()
                    obj.classification = obj.classify(obj.days_offset)

                    key = (receipt_no, line_no)
                    if key in objects_map:
                        # Duplicate within the incoming file; keep the last occurrence
                        error_logger.error("Duplicate in file (keeping last) ##: %s" % (line.strip()))
                    objects_map[key] = obj

                except Exception as e:
                    # Log error and continue to process remaining lines
                    error_logger.error(e, exc_info=True)
                    continue

            objects = list(objects_map.values())
            ReceiptLine.objects.bulk_create(objects,
                                     update_conflicts=True,
                                     unique_fields=['receipt', 'line'],
                                     update_fields=[
                                         "po_line",
                                         "received_quantity",
                                         "receipt_date",
                                         "days_offset",
                                         "amount_home_currency",
                                         "classification",
                                     ],)

            os.remove(file_copy)

            debug_logger.info("Updated Receipt Lines")

        except Exception as e:
            error_logger.error(e, exc_info=True)
