from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Labors'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"name": "John", "workcenter": "610", "calendar": "Default Labor"},
                {"name": "Mary", "workcenter": "615", "calendar": "Default Labor"},
                {"name": "Alice", "workcenter": "602", "calendar": "Default Labor"},
                {"name": "Bill", "workcenter": "637", "calendar": "Default Labor"},
                {"name": "Mike", "workcenter": "665", "calendar": "Default Labor"}
                ]

        for i in range(0, len(data)):
            obj = Labor()

            obj.name = data[i]["name"]
            obj.workcenter = WorkCenter.objects.get(code=data[i]["workcenter"])
            obj.calendar = Calendar.objects.get(name=data[i]["calendar"])

            objects.append(obj)

        Labor.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['name'],
                                      update_fields=["workcenter", "calendar"])