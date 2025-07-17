from django.core.management.base import BaseCommand
from django.core.management import call_command
from datetime import date

class Command(BaseCommand):
    help = 'Update Data'

    def handle(self, *args, **kwargs):
        today = date.today()

        # Update general dependencies
        call_command('create_work_centers')
        call_command('create_calendars')
        call_command('create_labors')
        call_command('create_shift_templates')
        call_command('create_calendar_days')
        call_command('create_items')
        call_command('create_tasks')
        call_command('create_machines')
        # call_command('create_purchase_orders')
        # call_command('create_purchase_order_lines')
        call_command('create_production_orders')
        call_command('create_production_order_operations')


