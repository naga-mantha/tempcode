from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Production Orders'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"production_order": "1000", "part_no": "item_1"},
                {"production_order": "1001", "part_no": "item_2"},
                ]

        for i in range(0, len(data)):
            obj = ProductionOrder()

            obj.production_order = data[i]["production_order"]
            obj.part_no = Item.objects.get(code=data[i]["part_no"])

            objects.append(obj)

        ProductionOrder.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['production_order'],
                                      update_fields=["part_no"])