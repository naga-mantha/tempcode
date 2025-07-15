from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Machines'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"code": "m_001", "name": "Machine 1", "calendar": "Default Machine"},
                {"code": "m_002", "name": "Machine 2", "calendar": "Default Machine"},
                {"code": "m_003", "name": "Machine 3", "calendar": "Default Machine"},
                {"code": "m_004", "name": "Machine 4", "calendar": "Default Machine"},
                {"code": "m_005", "name": "Machine 5", "calendar": "Default Machine"}]

        for i in range(0, len(data)):
            obj = Machine()

            obj.code = data[i]["code"]
            obj.name = data[i]["name"]
            obj.calendar = Calendar.objects.get(name=data[i]["calendar"])

            objects.append(obj)

        Machine.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['code'],
                                      update_fields=["name", "calendar"])