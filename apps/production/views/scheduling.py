from datetime import datetime, time, timedelta, date, timezone
from django.utils.timezone import make_aware
from apps.common.models import ProductionOrderSchedule, CalendarShift, CalendarDay, Labor, Machine, MachineDowntime
from apps.common.functions.lists import reverse_chunks
from django.core.exceptions import ValidationError
from django.db.models import Q

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

MAX_LOOKAHEAD_DAYS = 30
BACKWARD_PLANNING_ENGINE_FAIL = "Couldn't schedule using backward planning"
OTHER_ERROR = "Some other failure reason"
def try_schedule_operation(operation, direction="backward"):
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

    start_datetime = earliest
    remaining_time = operation.remaining_time
    i = 0
    days_without_schedule = 0
    full_start = None

    while remaining_time > 0:
        if direction == "forward":
            # build your machine candidates exactly as before
            machines = [operation.task.primary_machine] \
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

                    # apply your “i==0 / overlap‐filter” logic
                    if i == 0:
                        filtered = [(s, e) for s, e in inter if e > start_datetime]
                    else:
                        filtered = [
                            (s, e)
                            for s, e in inter
                            if e > start_datetime
                               and not (s < slot_end and e > slot_start)
                        ]

                    # clamp & drop zero-length
                    filtered = [(max(s, start_datetime), e) for s, e in filtered]
                    filtered = [(s, e) for s, e in filtered if (e - s).total_seconds() > 0]
                    if not filtered:
                        continue

                    # figure out how big a piece you can book
                    max_chunk = max((e - s).total_seconds() / 3600 for s, e in filtered)
                    chunk_to_book = min(remaining_time, max_chunk)

                    try:
                        s_fit, e_fit = find_slot_fit(
                            filtered,
                            duration_hours=chunk_to_book,
                            backward_planning=False
                        )
                    except ValueError:
                        continue

                    options.append((m, lab, s_fit, e_fit))

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
            remaining_time -= (slot_end - slot_start).total_seconds() / 3600
            slot_start, slot_end = slot_start, slot_end
            start_datetime = slot_end
            i += 1

    if full_start is None:
        raise ValidationError("Unable to schedule operation on any machine")

    full_end = slot_end
    return full_start, full_end

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

    window_start = min(start for start, _ in working_windows)
    window_end = max(end for _, end in working_windows)

    # build the time-window filter once
    time_q = Q(
        start_datetime__lt=window_end,
        end_datetime__gt=window_start,
    )

    # choose the right field depending on resource type
    if isinstance(resource, Machine):
        sched_q = Q(machine=resource)
    elif isinstance(resource, Labor):
        sched_q = Q(labor=resource)
    else:
        raise TypeError(f"Unsupported resource type: {type(resource)}")

    # Fetch scheduled operations overlapping any working window
    scheduled_ops = (
        ProductionOrderSchedule.objects
            .filter(time_q & sched_q)
            .order_by("start_datetime")
    )

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
