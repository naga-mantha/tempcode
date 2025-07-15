from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Tasks'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"code": "001", "name": "Cutting"},
                {"code": "002", "name": "Milling"},
                {"code": "003", "name": "Sharpening"},
                {"code": "004", "name": "Debur"},
                {"code": "005", "name": "Oiling"}]

        for i in range(0, len(data)):
            obj = Task()

            obj.code = data[i]["code"]
            obj.name = data[i]["name"]

            objects.append(obj)

        Task.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['code'],
                                      update_fields=["name"])