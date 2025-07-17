from django.core.management.base import BaseCommand
from apps.common.models import *
from datetime import date, datetime
from django.utils.timezone import make_aware

class Command(BaseCommand):
    help = 'Create Purchase Order Lines'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"order": "2000", "line": 10, "sequence": 0, "final_receive_date": make_aware(datetime(2025, 7, 6, 1, 0, 0)) },
                {"order": "2001", "line": 10, "sequence": 0, "final_receive_date": make_aware(datetime(2025, 7, 10, 0, 0, 0)) },
                ]

        for i in range(0, len(data)):
            obj = PurchaseOrderLine()

            obj.order = PurchaseOrder.objects.get(order=data[i]["order"])
            obj.line = data[i]["line"]
            obj.sequence = data[i]["sequence"]
            obj.final_receive_date = data[i]["final_receive_date"]

            objects.append(obj)

        PurchaseOrderLine.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['order', 'line' , 'sequence'],
                                      update_fields=["final_receive_date"])