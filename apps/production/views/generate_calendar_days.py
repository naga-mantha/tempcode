from datetime import timedelta, date
from apps.common.models import Calendar, CalendarDay, ShiftTemplate, CalendarShift

def generate_calendar_with_shifts(calendars: list, start_date: date, end_date: date, work_weekdays=None, shift_templates=None):
    """
    Auto-generates CalendarDay + CalendarShift for one or more calendars.
    Handles night shifts that extend past midnight.

    :param calendars: List of Calendar instances
    :param start_date: Start of range (inclusive)
    :param end_date: End of range (inclusive)
    :param work_weekdays: List of working weekdays (0=Mon, ..., 6=Sun)
    :param shift_templates: List of ShiftTemplate instances
    """
    if shift_templates is None:
        shift_templates = []
    if work_weekdays is None:
        work_weekdays = [0, 1, 2, 3, 4]
    for calendar in calendars:
        current_date = start_date

        while current_date <= end_date:
            is_working = current_date.weekday() in work_weekdays

            # Create or get CalendarDay
            cal_day, _ = CalendarDay.objects.get_or_create(
                calendar=calendar,
                date=current_date,
                defaults={"is_working_day": is_working}
            )

            if not is_working:
                current_date += timedelta(days=1)
                continue

            for shift in shift_templates:
                shift_start = shift.start_time
                shift_end = shift.end_time

                # Always create the shift for the day it starts
                CalendarShift.objects.get_or_create(
                    calendar_day=cal_day,
                    shift_template=shift
                )

                # Handle midnight-crossing shifts
                if shift_end <= shift_start:
                    next_date = current_date + timedelta(days=1)
                    next_day, _ = CalendarDay.objects.get_or_create(
                        calendar=calendar,
                        date=next_date,
                        defaults={"is_working_day": True}
                    )
                    # Note: no shift assignment for next day, just marking it "working"

            current_date += timedelta(days=1)
