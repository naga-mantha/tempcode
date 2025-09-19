from django.core.management.base import BaseCommand
from apps.common.models import *
from datetime import datetime, time, timedelta, date
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Daily'

    def handle(self, *args, **kwargs):
        PurchaseMrpMessage.objects.all().delete()

        call_command('create_purchase_mrp_msgs')
