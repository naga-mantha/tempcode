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
  help = 'Create Sales Orders'

  def handle(self, *args, **kwargs):
    try:
      if status == "DEV":
        file = "C:/Users/n.mantha/Desktop/datafiles/Sale-Orders-"
      else:
        file = "C:/inetpub/wwwroot/reports/Sale-Orders-"

      file_copy = files.read_text_contents(file, ["Date", "MAI", "ELIMETAL", "Order",  "-"])
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
            obj = SalesOrder()
            obj.order = currentline[0].strip()
            obj.customer = None if currentline[1].strip()=="" else BusinessPartner.objects.get_or_create(code=currentline[1].strip())[0]

            objects.append(obj)

      SalesOrder.objects.bulk_create(objects,
                                update_conflicts=True,
                                unique_fields=['order'],
                                update_fields=["customer"])

      os.remove(file_copy)

      debug_logger.info("Updated Sales Orders")

    except Exception as e:
      error_logger.error(e, exc_info=True)