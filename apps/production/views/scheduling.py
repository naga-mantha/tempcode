from datetime import datetime, time, timedelta, date, timezone
from django.utils.timezone import make_aware, now
from apps.common.models import ProductionOrderSchedule, CalendarShift, CalendarDay, Labor, Machine, MachineDowntime
from apps.common.functions.lists import reverse_chunks
from django.core.exceptions import ValidationError
from django.db.models import Q

EPSILON_HOURS = 1e-6   # ~0.000001 h ≈ 0.0036 s
MAX_LOOKAHEAD_DAYS = 700
BACKWARD_PLANNING_ENGINE_FAIL = "Couldn't schedule using backward planning"
OTHER_ERROR = "Some other failure reason"
def try_schedule_operation(operation, direction="backward"):
    print("This is operation: ", operation)
    """
    Attempts to schedule `operation` using finite-capacity logic,
    respecting prev_operation/next_operation. Returns (start, end) or None.
    """

    # For forward planning, check when the previous operation will be completed and set the current operation start time to that
    if ProductionOrderSchedule.objects.filter(operation=operation.prev_operation, schedule_state="scheduled").exists():
        prev_qs = ProductionOrderSchedule.objects.filter(operation=operation.prev_operation, schedule_state="scheduled")
        prev_op = prev_qs.first()
        earliest = max(operation.required_start, prev_op.end_datetime)
    else:
        earliest = operation.required_start

    # Check for OP PO date and make sure the start date is after receving date
    if operation.prev_operation and operation.prev_operation.op_po:
        po_rec_dt = operation.prev_operation.op_po.final_receive_date
        earliest = max(earliest, po_rec_dt)

    start_datetime = max(earliest, now())
    remaining_time = operation.remaining_time
    i = 0
    days_without_schedule = 0
    full_start = None

    while remaining_time > 0:
        print(operation, "-------", start_datetime)

        if direction == "forward":
            # build your machine candidates exactly as before
            machines = [operation.machine] \
                       + list(operation.task.alternate_machines.all())

            # pull **all** labors in the op’s workcenter
            labors = operation.workcenter.labor_set.all()

            options = []  # will hold (machine, labor, start, end)

            for m in machines:
                m_slots = get_available_slots(m, start_datetime)
                if not m_slots:
                    continue

                for lab in labors:
                    l_slots = get_available_slots(lab, start_datetime)
                    if not l_slots:
                        continue

                    # intersect that labor’s slots with the machine’s
                    inter = intersect_slots(l_slots, m_slots)
                    if not inter:
                        continue

                    # clamp each slot by the cursor
                    base_cursor = start_datetime if i == 0 else slot_end
                    clamped = [
                        (max(s, base_cursor), e)
                        for (s, e) in inter
                        if e > base_cursor
                    ]
                    # drop any micro-slots
                    clamped = [
                        (s, e) for (s, e) in clamped
                        if (e - s).total_seconds() / 3600 > EPSILON_HOURS
                    ]
                    if not clamped:
                        continue

                    # for each clamped slot, book as much as fits
                    for slot_start, slot_end in clamped:
                        slot_hours = (slot_end - slot_start).total_seconds() / 3600
                        to_book = min(remaining_time, slot_hours)
                        if to_book <= EPSILON_HOURS:
                            continue

                        options.append((
                            m,
                            lab,
                            slot_start,
                            slot_start + timedelta(hours=to_book)
                        ))

            if not options:
                # no (machine,lab) combo could fit → advance day and retry
                start_datetime += timedelta(days=1)
                days_without_schedule += 1
                if days_without_schedule > MAX_LOOKAHEAD_DAYS:
                    raise RuntimeError("…")
                continue

            # pick the (machine, labor) with the earliest start
            scheduled_machine, scheduled_labor, slot_start, slot_end = min(
                options, key=lambda x: x[2]
            )

            # persist that chunk
            ProductionOrderSchedule.objects.create(
                operation=operation,
                machine=scheduled_machine,
                labor=scheduled_labor,
                start_datetime=slot_start,
                end_datetime=slot_end,
                schedule_state="scheduled",
            )

            # record overall start on first piece
            if i == 0:
                full_start = slot_start

            # advance your cursor
            booked_h = (slot_end - slot_start).total_seconds() / 3600
            remaining_time -= booked_h
            start_datetime = slot_end
            i += 1

            # clamp small remainders
            if remaining_time <= EPSILON_HOURS:
                remaining_time = 0

    if full_start is None:
        raise ValidationError("Unable to schedule operation on any machine")

    full_end = slot_end
    return full_start, full_end


def get_available_slots(resource, date):
    """
    Returns a list of available (start, end) datetime slots for the given resource
    (Labor or Machine) on a specific date, honoring the resource’s calendar,
    its assigned shifts, and any vacations or downtimes.
    """

    # 1) Respect the calendar (holidays/weekends)
    calendar = resource.calendar
    try:
        cal_day = CalendarDay.objects.get(
            calendar=calendar,
            date=date,
            is_working_day=True
        )
    except CalendarDay.DoesNotExist:
        return []  # Non-working day for this calendar

    # 2) If resource is a Labor, check for vacations
    if isinstance(resource, Labor):
        for vac in resource.vacations.all():
            if vac.covers(date):
                return []  # Labor is on vacation

    # 3) Get only the shifts this resource can actually work
    if isinstance(resource, Labor):
        # assumes you’ve added a M2M: CalendarShift.labours → Labor
        calendar_shifts = (
            CalendarShift.objects
                .filter(calendar_day=cal_day, labours=resource)
                .select_related("shift_template")
        )
    else:
        # machines see every shift on their calendar
        calendar_shifts = (
            CalendarShift.objects
                .filter(calendar_day=cal_day)
                .select_related("shift_template")
        )

    if not calendar_shifts.exists():
        return []  # No shifts → no work for this resource

    # 4) Build working windows for each shift
    working_windows = []
    for shift in calendar_shifts:
        start_time = shift.shift_template.start_time
        end_time   = shift.shift_template.end_time

        start_dt = make_aware(datetime.combine(date, start_time))
        # handle overnight shifts
        if end_time < start_time:
            end_dt = make_aware(
                datetime.combine(date + timedelta(days=1), end_time)
            )
        else:
            end_dt = make_aware(datetime.combine(date, end_time))

        working_windows.append((start_dt, end_dt))

    window_start = min(s for s, _ in working_windows)
    window_end   = max(e for _, e in working_windows)

    # 5) Find any existing booked intervals in that window
    time_q = Q(start_datetime__lt=window_end,
               end_datetime__gt=window_start)
    if isinstance(resource, Machine):
        sched_q = Q(machine=resource)
    else:
        sched_q = Q(labor=resource)

    scheduled_ops = (
        ProductionOrderSchedule.objects
            .filter(time_q & sched_q)
            .order_by("start_datetime")
    )

    blocked = [(op.start_datetime, op.end_datetime)
               for op in scheduled_ops]

    # 6) Add machine downtimes
    if isinstance(resource, Machine):
        dt_windows = MachineDowntime.objects.filter(
            machine=resource,
            start_dt__lt=window_end,
            end_dt__gt=window_start
        ).order_by("start_dt")
        blocked += [(dt.start_dt, dt.end_dt) for dt in dt_windows]

    # 7) Subtract blocked intervals from each shift window
    free_slots = []
    for win_start, win_end in working_windows:
        current = win_start
        for block_start, block_end in blocked:
            if block_end <= current or block_start >= win_end:
                continue
            if current < block_start:
                free_slots.append((current, block_start))
            current = max(current, block_end)
        if current < win_end:
            free_slots.append((current, win_end))

    return free_slots


def intersect_slots(slots_a, slots_b):
    """
    Given two lists of (start, end) datetime tuples,
    return the overlapping time windows as a list of (start, end).
    """

    i, j = 0, 0
    result = []

    while i < len(slots_a) and j < len(slots_b):
        start_a, end_a = slots_a[i]
        start_b, end_b = slots_b[j]

        # Find overlap between the two slots
        latest_start = max(start_a, start_b)
        earliest_end = min(end_a, end_b)

        # If they overlap, add to result
        if latest_start < earliest_end:
            result.append((latest_start, earliest_end))

        # Move the pointer with the earlier end
        if end_a < end_b:
            i += 1
        else:
            j += 1

    return result

def find_slot_fit(slots, duration_hours: int, backward_planning=False):
    """
    Returns the first (start, end) slot that fits the required duration in minutes.
    slots --> Avaialability from intersect_slots function (start and end times)
    """

    required_duration = timedelta(hours=duration_hours)

    for start, end in slots:
        # print("Start: ", start, " , End: ", end, " , slots: ", slots)

        if backward_planning:
            req_start = end - required_duration
            req_end = end

            if req_start < start:
                req_start = start

            return (req_start, req_end)

        else:
            req_start = start
            req_end = start + required_duration

            if req_end > end:
                req_end = end

            return (req_start, req_end)
