from django.core.management.base import BaseCommand
from apps.common.models import *
from apps.production.views.generate_calendar_days import generate_calendar_with_shifts
from datetime import date

class Command(BaseCommand):
    help = 'Create Calendar Days'

    def handle(self, *args, **kwargs):
        cal1 = Calendar.objects.get(name="Default Machine")
        cal2 = Calendar.objects.get(name="Default Labor")

        day_shift = ShiftTemplate.objects.get(name="Day Shift")
        night_shift = ShiftTemplate.objects.get(name="Night Shift")

        generate_calendar_with_shifts(
            calendars=[cal1, cal2],
            start_date=date(2025, 7, 1),
            end_date=date(2025, 12, 31),
            work_weekdays=[0, 1, 2, 3, 4],  # Mon–Fri
            shift_templates=[day_shift, night_shift]
        )

