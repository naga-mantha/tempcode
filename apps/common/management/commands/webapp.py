from django.core.management.base import BaseCommand
from apps.common.models import *
from datetime import datetime, time, timedelta, date
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Daily'

    def handle(self, *args, **kwargs):
        PurchaseMrpMessage.objects.all().delete()
        PlannedPurchaseOrder.objects.all().delete()

        call_command('update_exchange_rates')
        call_command('create_business_partners')
        call_command('create_items')
        call_command('create_purchase_orders')
        call_command('create_purchase_order_lines')
        call_command('create_receipts')
        call_command('create_receipts_lines')
        call_command('create_planned_purchase_orders')
        call_command('create_purchase_mrp_msgs')






