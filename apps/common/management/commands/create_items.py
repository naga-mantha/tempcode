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
    help = 'Update Items'

    def handle(self, *args, **kwargs):
        try:
            if status == "DEV":
                file = "C:/Users/n.mantha/Desktop/datafiles/Parts-"
            else:
                file = "C:/inetpub/wwwroot/reports/Parts-"
            file_copy = files.read_text_contents(file, ["Date:", "MAI -", "ELIMETAL -", "Item Group", "-",])
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

                    part_no = currentline[2].strip()
                    description = currentline[3].strip()

                    if not part_no.startswith("PROG02") and description != "DO NOT USE":
                        obj = Item()
                        obj.code = part_no
                        obj.description = description

                        objects.append(obj)

            Item.objects.bulk_create(objects,
                                     update_conflicts=True,
                                     unique_fields=['code'],
                                     update_fields=["description"])

            os.remove(file_copy)

            debug_logger.info("Updated Parts and Item Groups")

        except Exception as e:
            error_logger.error(e, exc_info=True)