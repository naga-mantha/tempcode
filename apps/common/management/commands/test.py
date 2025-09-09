from django.core.management.base import BaseCommand
from apps.common.models import *
from datetime import datetime, time, timedelta, date

class Command(BaseCommand):
    help = 'Delete'

    def handle(self, *args, **kwargs):
        ReceiptLine.objects.all().delete()
        Receipt.objects.all().delete()
        PurchaseOrderLine.objects.all().delete()
        PurchaseOrder.objects.all().delete()

