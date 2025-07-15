from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Work Centers'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"code": "610", "name": "LARGE LATHE"},
                {"code": "615", "name": "HORIZONTAL MILLING"},
                {"code": "602", "name": "5 AXES"},
                {"code": "637", "name": "DEBURR"},
                {"code": "665", "name": "RED OIL"}
                ]

        for i in range(0, len(data)):
            obj = WorkCenter()

            obj.code = data[i]["code"]
            obj.name = data[i]["name"]

            objects.append(obj)

        WorkCenter.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['code'],
                                      update_fields=["name"])