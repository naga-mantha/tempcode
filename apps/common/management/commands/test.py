from django.core.management.base import BaseCommand
from apps.common.models import *
from apps.production.views.scheduling import *
from datetime import datetime, time, timedelta, date

class Command(BaseCommand):
    help = 'Create Calendar Days'

    def handle(self, *args, **kwargs):
        labor_resource = Labor.objects.get(name="John")
        labor_date = date(2025, 7, 9)
        print("Available Slots for Labor:")
        slot_labor = get_available_slots(labor_resource, labor_date)
        print(slot_labor)
        print("---------------------------------------------------------------------------")

        machine_resource = Machine.objects.get(code="m_001")
        machine_date = date(2025, 7, 9)
        print("Available Slots for Machine:")
        slot_machine = get_available_slots(machine_resource, machine_date)
        print(slot_machine)
        print("---------------------------------------------------------------------------")

        print("Intersection:")
        intersection_slots = intersect_slots(slot_labor, slot_machine)
        print(intersection_slots)
        print("---------------------------------------------------------------------------")


        print(find_slot_fit((intersection_slots), duration_minutes=30))

        operation = ProductionOrderOperation.objects.get(operation=20)
        next_sched = operation.prev_operation
        print(next_sched)