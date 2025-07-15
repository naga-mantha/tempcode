from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Calendars'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"name": "Default Labor"},
                {"name": "Default Machine"},]

        for i in range(0, len(data)):
            obj = Calendar()

            obj.name = data[i]["name"]

            objects.append(obj)

        Calendar.objects.bulk_create(objects,
                                     update_conflicts=True,
                                     unique_fields=['name'],
                                     update_fields=["name"])