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
  help = 'Create Labors'

  def handle(self, *args, **kwargs):
    try:
      if status == "DEV":
        file = "C:/Users/n.mantha/Desktop/datafiles/Labors-"
      else:
        file = "C:/inetpub/wwwroot/reports/Labors-"

      file_copy = files.read_text_contents(file, ["Date", "MAI", "ELIMETAL", "Employee", " ", "-"])
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

          if currentline[0].strip() != "" and currentline[2].strip() != "":
            obj = Labor()
            obj.code = currentline[0].strip()
            obj.name = currentline[1].strip()
            obj.workcenter = None if currentline[2].strip()=="" else WorkCenter.objects.get_or_create(code=currentline[2].strip())[0]
            obj.calendar = Calendar.objects.get(name="Default Labor")

            objects.append(obj)

      Labor.objects.bulk_create(objects,
                                update_conflicts=True,
                                unique_fields=['code'],
                                update_fields=["name", "workcenter", "calendar"])

      os.remove(file_copy)

      debug_logger.info("Updated Labors")

    except Exception as e:
      error_logger.error(e, exc_info=True)
