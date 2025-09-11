from apps.common.models import *
from datetime import datetime, time, timedelta, date
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'AAAAAAAAAAAAA'

    def handle(self, *args, **kwargs):
        # ReceiptLine.objects.all().delete()
        # Receipt.objects.all().delete()
        # PurchaseOrderLine.objects.all().delete()
        # PurchaseOrder.objects.all().delete()
        # PlannedOrder.objects.all().delete()
        MrpMessage.objects.all().delete()

        # # PO Headers
        # call_command('excel_po_header')
        #
        # # Open PO Lines
        # call_command('excel_open_po_line')
        #
        # # Closed PO Lines + Receipts
        # call_command('excel_closed_po_line')
        # call_command('excel_receipt')
        # call_command('excel_receipt_lines')
        #
        # # Planned Orders
        # call_command('excel_planned_order')
        call_command('excel_text_mrp_msgs')

