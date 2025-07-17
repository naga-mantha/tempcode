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
  help = 'Create Production Order Operations'

  def handle(self, *args, **kwargs):
    try:
      if status == "DEV":
        file = "C:/Users/n.mantha/Desktop/datafiles/Work-Order-Operations-"
      else:
        file = "C:/inetpub/wwwroot/reports/Work-Order-Operations-"

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
            obj = ProductionOrderOperation()
            obj.production_order = None if currentline[0].strip()=="" else ProductionOrder.objects.get_or_create(production_order=currentline[0].strip())[0]
            obj.operation = currentline[7].strip()
            obj.task = None if currentline[10].strip()=="" else Task.objects.get_or_create(code=currentline[10].strip())[0]
            obj.workcenter = None if currentline[12].strip()=="" else WorkCenter.objects.get_or_create(code=currentline[12].strip())[0]
            obj.machine = None if currentline[14].strip()=="" else Machine.objects.get_or_create(code=currentline[14].strip())[0]
            obj.remaining_time = 1 if currentline[19].strip()==0 else currentline[19].strip()
            obj.required_start = None if currentline[15].strip() == "" else datetime.strptime(currentline[15].strip(), '%m/%d/%Y')

            objects.append(obj)

      ProductionOrderOperation.objects.bulk_create(objects,
                                update_conflicts=True,
                                unique_fields=['production_order', 'operation'],
                                update_fields=["task", "workcenter", "machine", "remaining_time", "required_start"])

      os.remove(file_copy)

      debug_logger.info("Updated Production Order Operations")

    except Exception as e:
      error_logger.error(e, exc_info=True)