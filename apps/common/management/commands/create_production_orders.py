from django.core.management.base import BaseCommand
from apps.common.models import *
from apps.common.functions import files
import os
import environ
import re
import logging

env = environ.Env()
environ.Env.read_env()
status = env('STATUS')
error_logger = logging.getLogger(name="app_errors")
debug_logger = logging.getLogger(__name__)

class Command(BaseCommand):
  help = 'Create Production Orders'

  def handle(self, *args, **kwargs):
    try:
      if status == "DEV":
        file = "C:/Users/n.mantha/Desktop/datafiles/Work-Orders-"
      else:
        file = "C:/inetpub/wwwroot/reports/Work-Orders-"

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
            obj = ProductionOrder()
            obj.production_order = currentline[0].strip()
            obj.part_no = None if currentline[1].strip()=="" else Item.objects.get_or_create(code=currentline[1].strip())[0]

            objects.append(obj)

      ProductionOrder.objects.bulk_create(objects,
                                update_conflicts=True,
                                unique_fields=['production_order'],
                                update_fields=["part_no"])

      os.remove(file_copy)

      debug_logger.info("Updated Production Orders")

    except Exception as e:
      error_logger.error(e, exc_info=True)