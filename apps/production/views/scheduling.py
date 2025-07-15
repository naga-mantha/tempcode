from datetime import datetime, time, timedelta, date, timezone
from django.utils.timezone import make_aware
from apps.common.models import ProductionOrderSchedule, CalendarShift, CalendarDay, ProductionOrderOperation, Machine, MachineDowntime
from apps.common.functions.lists import reverse_chunks

# def try_schedule_operation(operation, direction="backward") -> tuple[datetime, datetime] | None:
#     """
#     Attempts to schedule `operation` using finite-capacity logic,
#     respecting prev_operation/next_operation. Returns (start, end) or None.
#     """
#     remaining_minutes = int((operation.remaining_time or 0) * 60)
#     scheduled_blocks  = []
#
#     # ─── 1) SET UP THE DEPENDENCY POINTER ─────────────────────────
#     if direction == "forward":
#         if operation.prev_operation:
#             prev_sched = (
#                 ProductionOrderSchedule.objects
#                 .filter(operation=operation.prev_operation, schedule_state="scheduled")
#                 .order_by("-end_datetime")
#                 .first()
#             )
#             pointer = prev_sched.end_datetime if prev_sched else operation.required_start
#         else:
#             pointer = operation.required_start
#     else:
#         if operation.next_operation:
#             next_sched = (
#                 ProductionOrderSchedule.objects
#                 .filter(operation=operation.next_operation, schedule_state="scheduled")
#                 .order_by("start_datetime")
#                 .first()
#             )
#             pointer = next_sched.start_datetime if next_sched else operation.required_end
#         else:
#             pointer = operation.required_end
#
#     # normalize to aware datetime
#     if not isinstance(pointer, datetime):
#         pointer = make_aware(datetime.combine(pointer, time.min))
#
#     max_days = 30
#
#     # ─── 2) WALK DAYS ──────────────────────────────────────────────
#     for _ in range(max_days):
#         day = pointer.date()
#         machine_slots = get_available_slots(operation.machine, day)
#         labor_slots   = get_available_slots(operation.labor, day)
#         joint_slots   = intersect_slots(machine_slots, labor_slots)
#
#         # ── ensure correct ordering per direction ───────────────────
#         if direction == "backward":
#             joint_slots.sort(key=lambda rng: rng[1], reverse=True)
#         else:
#             joint_slots.sort(key=lambda rng: rng[0])
#
#         for slot_start, slot_end in joint_slots:
#             # clamp to dependency bound
#             if direction == "forward":
#                 if slot_end <= pointer:
#                     continue
#                 slot_start = max(slot_start, pointer)
#             else:
#                 if slot_start >= pointer:
#                     continue
#                 slot_end   = min(slot_end, pointer)
#
#             slot_dur = (slot_end - slot_start).total_seconds() / 60
#             if slot_dur <= 0:
#                 continue
#
#             fit = min(remaining_minutes, slot_dur)
#             if direction == "forward":
#                 block_start = slot_start
#                 block_end   = slot_start + timedelta(minutes=fit)
#             else:
#                 block_end   = slot_end
#                 block_start = slot_end - timedelta(minutes=fit)
#
#             scheduled_blocks.append((block_start, block_end))
#             remaining_minutes -= fit
#             # move pointer so we don’t overlap this block
#             pointer = block_end if direction == "forward" else block_start
#
#             if remaining_minutes <= 0:
#                 break
#         if remaining_minutes <= 0:
#             break
#
#         # ── roll pointer to the next / previous day boundary ─────────
#         tz = pointer.tzinfo
#         if direction == "forward":
#             next_day = day + timedelta(days=1)
#             pointer  = datetime.combine(next_day, time.min, tzinfo=tz)
#         else:
#             prev_day = day - timedelta(days=1)
#             pointer  = datetime.combine(prev_day, time.max, tzinfo=tz)
#
#     # ─── 3) FINALIZE ───────────────────────────────────────────────
#     if remaining_minutes > 0:
#         return None
#
#     full_start = min(s for s, e in scheduled_blocks)
#     full_end   = max(e for s, e in scheduled_blocks)
#
#     ProductionOrderSchedule.objects.create(
#         operation=operation,
#         start_datetime=full_start,
#         end_datetime=full_end,
#         schedule_state="scheduled"
#     )
#
#     return (full_start, full_end)

BACKWARD_PLANNING_ENGINE_FAIL = "Couldn't schedule using backward planning"
OTHER_ERROR = "Some other failure reason"
def try_schedule_operation(operation, direction="backward"):
    """
    Attempts to schedule `operation` using finite-capacity logic,
    respecting prev_operation/next_operation. Returns (start, end) or None.
    """

    # For forward planning, check when the previous operation will be completed and set the current operation start time to that
    if ProductionOrderSchedule.objects.filter(operation=operation.prev_operation, schedule_state="scheduled").exists():
        prev_op = ProductionOrderSchedule.objects.get(operation=operation.prev_operation, schedule_state="scheduled")
        earliest = max(operation.required_start, prev_op.end_datetime)
    else:
        earliest = operation.required_start

    # Check for OP PO date and make sure the start date is after receving date
    if operation.prev_operation and operation.prev_operation.op_po:
        po_rec_dt = operation.prev_operation.op_po.final_receive_date
        earliest = max(earliest, po_rec_dt)

    start_datetime = earliest

    #ToDo: Deal with this in backward planning
    original_end_datetime = operation.required_end
    end_datetime = original_end_datetime


    remaining_time = operation.remaining_time
    i = 0

    # START LOOP
    while remaining_time > 0:
        if direction=="backward":
            slot_labor = get_available_slots(operation.labor, end_datetime)
            slot_machine = get_available_slots(operation.machine, end_datetime)
            intersection_slots = intersect_slots(slot_labor, slot_machine)

            # Keep only the (start,end) intersection times where the start < original_end_datetime
            intersection_slots = [
                (start, end)
                for start, end in intersection_slots
                if start <= original_end_datetime
            ]

            # If end is greater than original_end_datetime, then force it to original_end_datetime
            intersection_slots = [
                (start,
                 original_end_datetime if end > original_end_datetime else end)
                for start, end in intersection_slots
            ]


            intersection_slots = intersection_slots[::-1]  # Reverse the time slots (so that night shifts gets scheduled first before morning shoft
            slot_start, slot_end = find_slot_fit((intersection_slots), duration_hours=remaining_time, backward_planning=True)

            remaining_time = remaining_time - (slot_end - slot_start).total_seconds()/3600   #Convert seconds to hours
            end_datetime = end_datetime - timedelta(days=1)

            production_start = slot_start
            production_end = slot_end



            if production_end and i==0:
                full_end = production_end
                i = i + 1

            if ProductionOrderSchedule.objects.filter(operation=operation.prev_operation, schedule_state="scheduled").exists():
                prev_op = ProductionOrderSchedule.objects.get(operation=operation.prev_operation, schedule_state="scheduled")
                prev_op_end_time = prev_op.end_datetime
                if production_start < prev_op_end_time:
                    return BACKWARD_PLANNING_ENGINE_FAIL


        if direction=="forward":
            slot_labor = get_available_slots(operation.labor, start_datetime)
            slot_machine = get_available_slots(operation.machine, start_datetime)
            intersection_slots = intersect_slots(slot_labor, slot_machine)

            # If its a holiday and there are no slots, move to next day
            if not intersection_slots:
                start_datetime = start_datetime + timedelta(days=1)
                continue  # restart the loop using the new start_datetime

            # On first loop, keep only the (start,end) intersection times when the end > start_datetime
            if i == 0:
                filtered = [(s, e) for s, e in intersection_slots if e > start_datetime]

            # Keep only the (start,end) intersection times when the end > start_datetime +
            # Drop any booked slots (start < slot_end and end > slot_start)
            else:
                filtered = [
                    (s, e)
                    for s, e in intersection_slots
                    if e > start_datetime and not (s < slot_end and e > slot_start)
                ]

            # If start is less than original_start_datetime, then force it to original_start_datetime
            filtered = [(max(s, start_datetime), e) for s, e in filtered]

            # Make sure the start and end are not the same
            filtered = [(s, e) for s, e in filtered if (e - s).total_seconds() > 0]

            intersection_slots = filtered

            # Find and book the next chunk
            slot_start, slot_end = find_slot_fit(intersection_slots, duration_hours=remaining_time, backward_planning=False)
            remaining_time -= (slot_end - slot_start).total_seconds() / 3600
            print("Slot Start:", slot_start, "Slot End:", slot_end, "Remaining:", remaining_time)

            # Advance your cursor
            start_datetime = slot_end

            # Record the true production start
            if i == 0:
                full_start = slot_start
            i += 1


    # Outside Loop
    if direction=="backward":
        full_start = production_start
        full_end = full_end
    else:
        full_start = full_start
        full_end = slot_end

    ProductionOrderSchedule.objects.create(
            operation=operation,
            start_datetime=full_start,
            end_datetime=full_end,
            schedule_state="scheduled"
        )

    return None

def get_available_slots(resource, date):
    """
    Returns a list of available (start, end) datetime slots for the given resource (Labor or Machine)
    on a specific date using the resource's calendar and shift templates.
    """

    # Get calendar and working day
    calendar = resource.calendar
    try:
        cal_day = CalendarDay.objects.get(calendar=calendar, date=date, is_working_day=True)
    except CalendarDay.DoesNotExist:
        return []  # Non-working day

    # Get all assigned shifts for the day
    calendar_shifts = CalendarShift.objects.filter(calendar_day=cal_day).select_related("shift_template")

    if not calendar_shifts.exists():
        return []  # No shift → no work

    # Build working windows for each shift
    working_windows = []
    for shift in calendar_shifts:
        start_time = shift.shift_template.start_time
        end_time = shift.shift_template.end_time

        start_dt = make_aware(datetime.combine(date, start_time))
        if end_time < start_time:
            # Shift crosses midnight
            end_dt = make_aware(datetime.combine(date + timedelta(days=1), end_time))
        else:
            end_dt = make_aware(datetime.combine(date, end_time))

        working_windows.append((start_dt, end_dt))

    # Fetch scheduled operations overlapping any working window
    scheduled_ops = ProductionOrderSchedule.objects.filter(
        operation__in=resource.operations.all(),
        start_datetime__lt=max(end for _, end in working_windows),
        end_datetime__gt=min(start for start, _ in working_windows)
    ).order_by("start_datetime")

    # Build list of blocked intervals
    blocked = [(op.start_datetime, op.end_datetime) for op in scheduled_ops]

    # Fold in any planned downtimes for this machine ---
    if isinstance(resource, Machine):
        dt_windows = MachineDowntime.objects.filter(
            machine=resource,
            start_dt__lt=max(end for _, end in working_windows),
            end_dt__gt=min(start for start, _ in working_windows)
        ).order_by("start_dt")

        # extend the blocked list
        blocked += [(dt.start_dt, dt.end_dt) for dt in dt_windows]

    # Subtract blocked slots from each shift window
    free_slots = []
    for window_start, window_end in working_windows:
        current = window_start
        for block_start, block_end in blocked:
            if block_end <= current or block_start >= window_end:
                continue
            if current < block_start:
                free_slots.append((current, block_start))
            current = max(current, block_end)
        if current < window_end:
            free_slots.append((current, window_end))

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
