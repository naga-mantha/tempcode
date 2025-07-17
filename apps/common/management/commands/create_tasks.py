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
    help = 'Update Tasks'

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                file = "C:/Users/n.mantha/Desktop/datafiles/Tasks-"
            else:
                file = "C:/inetpub/wwwroot/reports/Tasks-"
            file_copy = files.read_text_contents(file, ["Date", "MAI -", "ELIMETAL -", "Task", "-",])
            objects = []

            # Open the copied file and read the contents
            with open(file_copy, "r") as f:
                lines = f.readlines()

            for line in lines:
                line_check = files.check_file_line(line)

                if line_check == False:
                    error_logger.error("Line Error ##: %s" % (line))

                else:
                    currentline = line.split("|")

                    if currentline[0].strip() != "":
                        obj = Task()
                        obj.code = currentline[0].strip()
                        obj.name = currentline[1].strip()
                        obj.primary_machine = Machine.objects.get_or_create(code="Default")[0] if currentline[6].strip()=="" \
                            else Machine.objects.get_or_create(code=currentline[6].strip())[0]

                        objects.append(obj)

            Task.objects.bulk_create(objects,
                                     update_conflicts=True,
                                     unique_fields=['code'],
                                     update_fields=["name", "primary_machine"])

            os.remove(file_copy)

            debug_logger.info("Updated Tasks")

        except Exception as e:
            error_logger.error(e, exc_info=True)
