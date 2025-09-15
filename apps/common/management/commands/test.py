from django.core.management.base import BaseCommand
from apps.common.models import *
from datetime import datetime, time, timedelta, date
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Delete'

    def handle(self, *args, **kwargs):
        # PurchaseMrpMessage.objects.all().delete()
        # PlannedPurchaseOrder.objects.all().delete()
        # ReceiptLine.objects.all().delete()
        # Receipt.objects.all().delete()
        # PurchaseOrderLine.objects.all().delete()
        # PurchaseOrder.objects.all().delete()
        # SalesOrderLine.objects.all().delete()
        # SalesOrder.objects.all().delete()
        # BusinessPartner.objects.all().delete()
        # Item.objects.all().delete()
        # ItemType.objects.all().delete()
        # ItemGroup.objects.all().delete()
        # ItemGroupType.objects.all().delete()
        # Program.objects.all().delete()
        # MrpRescheduleDaysClassification.objects.all().delete()
        # PurchaseOrderCategory.objects.all().delete()
        # PurchaseSettings.objects.all().delete()
        # PurchaseTimelinessClassification.objects.all().delete()
        # UOM.objects.all().delete()

        # call_command('update_exchange_rates')
        # call_command('create_business_partners')
        # call_command('create_items')
        # call_command('create_purchase_orders')
        call_command('create_purchase_order_lines')
        # call_command('create_receipts')
        # call_command('create_receipts_lines')
        # call_command('create_planned_purchase_orders')
        # call_command('create_purchase_mrp_msgs')






