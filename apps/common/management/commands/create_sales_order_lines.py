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
  help = 'Create Sales Order Lines'

  def handle(self, *args, **kwargs):
    try:
      if status == "DEV":
        file = "C:/Users/n.mantha/Desktop/datafiles/Sale-Order-Lines-"
      else:
        file = "C:/inetpub/wwwroot/reports/Sale-Order-Lines-"

      file_copy = files.read_text_contents(file, ["Date", "MAI", "ELIMETAL", "Order", "-"])
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
            obj = SalesOrderLine()
            obj.sales_order = None if currentline[0].strip()=="" else SalesOrder.objects.get_or_create(order=currentline[0].strip())[0]
            obj.sales_order_line = currentline[1].strip()
            obj.sequence = currentline[2].strip()
            obj.item = None if currentline[3].strip()=="" else Item.objects.get_or_create(code=currentline[3].strip())[0]
            obj.d2_date = None if currentline[5].strip() == "" else datetime.strptime(currentline[5].strip(), '%m/%d/%Y')
            obj.d3_date = None if currentline[6].strip() == "" else datetime.strptime(currentline[6].strip(), '%m/%d/%Y')
            obj.back_order = float(currentline[11].strip())

            objects.append(obj)

      SalesOrderLine.objects.bulk_create(objects,
                                update_conflicts=True,
                                unique_fields=['sales_order', 'sales_order_line', 'sequence'],
                                update_fields=["item", "d2_date", "d3_date", "back_order"])

      os.remove(file_copy)

      debug_logger.info("Updated Sales Order Lines")

    except Exception as e:
      error_logger.error(e, exc_info=True)