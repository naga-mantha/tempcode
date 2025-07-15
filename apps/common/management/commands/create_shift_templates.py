from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Shift Templates'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"name": "Day Shift", "start_time": "08:00:00", "end_time": "17:00:00"},
                {"name": "Night Shift", "start_time": "18:00:00", "end_time": "03:00:00"},
                ]

        for i in range(0, len(data)):
            obj = ShiftTemplate()

            obj.name = data[i]["name"]
            obj.start_time = data[i]["start_time"]
            obj.end_time = data[i]["end_time"]

            objects.append(obj)

        ShiftTemplate.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['name'],
                                      update_fields=["start_time", "end_time"])