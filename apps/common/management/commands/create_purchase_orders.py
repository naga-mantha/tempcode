from django.core.management.base import BaseCommand
from apps.common.models import *

class Command(BaseCommand):
    help = 'Create Purchase Orders'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"order": "2000"},
                {"order": "2001"},
                ]

        for i in range(0, len(data)):
            obj = PurchaseOrder()

            obj.order = data[i]["order"]

            objects.append(obj)

        PurchaseOrder.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['order'],
                                      update_fields=["order"])