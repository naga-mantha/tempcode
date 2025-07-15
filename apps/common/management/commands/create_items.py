from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Items'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"code": "item_1", "description": "Piston"},
                {"code": "item_2", "description": "Cylinder"},
                {"code": "item_3", "description": "Main Fitting"},
                {"code": "item_4", "description": "Wheel Axle"},
                {"code": "item_5", "description": "Bushing"},
                {"code": "item_6", "description": "Pin"},]

        for i in range(0, len(data)):
            obj = Item()

            obj.code = data[i]["code"]
            obj.description = data[i]["description"]

            objects.append(obj)

        Item.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['code'],
                                      update_fields=["description"])