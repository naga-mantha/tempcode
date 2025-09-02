from django.core.management.base import BaseCommand
from apps.common.models import *
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
  help = 'Create Customer PO'

  def handle(self, *args, **kwargs):
    try:
      if status == "DEV":
        file = "C:/Users/n.mantha/Desktop/datafiles/Customer-PO-"
      else:
        file = "C:/inetpub/wwwroot/reports/Customer-PO-"

      file_copy = files.read_text_contents(file, ["Date", "MAI", "ELIMETAL", "Prdn", " ", "-"])
      objects = []

      # Open the copied file and read the contents
      with open(file_copy, "r") as f:
        lines = f.readlines()

      for line in lines:
        line_check = files.check_file_line(line)

        if not line_check:
          error_logger.error("Line Error ##: %s" % (line))

        else:
          currentline = line.split("|")

          if currentline[0].strip() != "":
            obj = CustomerPurchaseOrder()
            obj.customer_purchase_order = currentline[0].strip()
            obj.item = None if currentline[1].strip()=="" else Item.objects.get_or_create(code=currentline[1].strip())[0]
            obj.customer = BusinessPartner.objects.get_or_create(code="CUSCOL")[0]
            obj.d2_date = None if currentline[2].strip() == "" else datetime.strptime(currentline[2].strip(), '%Y-%m-%d')
            obj.back_order = float(currentline[3].strip())

            objects.append(obj)

      CustomerPurchaseOrder.objects.bulk_create(objects,
                                update_conflicts=True,
                                unique_fields=['customer_purchase_order'],
                                update_fields=["item", "customer", "d2_date", "back_order"])

      os.remove(file_copy)

      debug_logger.info("Updated Customer PO")

    except Exception as e:
      error_logger.error(e, exc_info=True)