# Khan
# two endpoints:
# get_event_instances - returns all ScheduleEvent rows for a template as JSON
# update_instance_status - lets user mark an instance completed or missed via the circles

import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware
from student_calendar.models import Event
from student_calendar.models.schedule_event import ScheduleEvent
from student_calendar.smart_planner_service import get_day_bitmask

@login_required
def get_event_instances(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    instances = ScheduleEvent.objects.filter(event=event).order_by('occurrence_index')

    instance_data = []
    for inst in instances:
        instance_data.append({
            'id': inst.id,
            'occurrence_index': inst.occurrence_index,
            'status': inst.status,
            'placed_start': inst.placed_start.strftime('%d %b %Y, %H:%M') if inst.placed_start else None,
            'placed_end': inst.placed_end.strftime('%H:%M') if inst.placed_end else None,
        })

    return JsonResponse({
        'event_id': event.id,
        'title': event.title,
        'max_instances': event.max_instances or 0,
        'duration': event.duration_format(),
        'category_colour': event.category.colour if event.category else '#888888',
        'importance': event.importance or 5,
        'instances': instance_data
    })


@login_required
def update_instance_status(request, pk):
    """Update the status of a ScheduleEvent (scheduled/completed/missed)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Bad request'}, status=400)

    instance = get_object_or_404(ScheduleEvent, pk=pk)
    if instance.event.user != request.user:
        return JsonResponse({'error': 'Not allowed'}, status=403)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    new_status = body.get('status')
    valid_statuses = [
        ScheduleEvent.Status.SCHEDULED,
        ScheduleEvent.Status.COMPLETED,
        ScheduleEvent.Status.MISSED,
    ]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Bad request'}, status=400)

    # Block jumping from CREATED straight to COMPLETED or MISSED.
    # An instance has to be placed on the calendar (SCHEDULED) first, otherwise
    # the completed page ends up showing instances that were never actually
    # on anyone's schedule - which looks like a data integrity bug.
    if instance.status == ScheduleEvent.Status.CREATED and new_status in (
        ScheduleEvent.Status.COMPLETED,
        ScheduleEvent.Status.MISSED,
    ):
        return JsonResponse(
            {'error': 'Instance must be scheduled before it can be marked completed or missed'},
            status=400,
        )

    instance.status = new_status
    instance.save()
    return JsonResponse({'ok': True, 'new_status': instance.status})




@login_required
def unplace_instance(request, pk):
    """Remove an instance from the grid: clear placed times and reset to CREATED."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Bad request'}, status=400)

    instance = get_object_or_404(ScheduleEvent, pk=pk)
    if instance.event.user != request.user:
        return JsonResponse({'error': 'Not allowed'}, status=403)

    # Completed / missed instances are historical — don't let them silently
    # revert to CREATED when the user drags them back to the sidebar or hits
    # "Remove from calendar". User should uncheck "mark as completed" first
    # (which flips the status back to SCHEDULED), then they can unplace.
    if instance.status in (
        ScheduleEvent.Status.COMPLETED,
        ScheduleEvent.Status.MISSED,
    ):
        return JsonResponse(
            {'error': 'Unmark the instance as completed before removing it from the calendar'},
            status=400,
        )

    instance.placed_start = None
    instance.placed_end = None
    instance.status = ScheduleEvent.Status.CREATED
    instance.save()
    return JsonResponse({'ok': True})

SENTINEL_YEAR = 1970


def _validate_placement(event, placed_start, placed_end):
    """Check placed_start/placed_end against the event template's constraints.
    Returns an error string if invalid, or None if ok.

    Three cases, matching the frontend logic:
      Case C — fully fixed (start+end real year): placement must match exactly.
      Case B — time-locked (sentinel year 1970): time-of-day must match, date is free.
      repeat_days: if set, placed_start weekday bit must be in the mask.
    """
    if not placed_start:
        return 'placed_start required'

    # Case C — placement must equal the event's start/end to the minute
    if event.start and event.end and event.start.year != SENTINEL_YEAR:
        if placed_start != event.start or (placed_end and placed_end != event.end):
            return 'This is a fixed event and must be placed at its set date and time.'
        return None

    # Case B — sentinel-year time-only events: enforce the time, not the date
    if event.start and event.start.year == SENTINEL_YEAR:
        if placed_start.time() != event.start.time():
            return 'This event has a fixed time and must be placed at that time.'
        if event.end and placed_end and placed_end.time() != event.end.time():
            return 'This event has a fixed end time and must be placed at that time.'

    # repeat_days — weekday of placed_start must be in the mask
    if event.repeat_days:
        day_bit = get_day_bitmask(placed_start.date())
        if not (event.repeat_days & day_bit):
            return 'This event can only be placed on its allowed days of the week.'

    return None


@login_required
def place_instance(request, pk):
    """Place an instance on the calendar: set placed times and mark SCHEDULED."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Bad request'}, status=400)

    instance = get_object_or_404(ScheduleEvent, pk=pk)
    if instance.event.user != request.user:
        return JsonResponse({'error': 'Not allowed'}, status=403)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    placed_start = body.get('placed_start')
    placed_end = body.get('placed_end')

    if not placed_start:
        return JsonResponse({'error': 'placed_start required'}, status=400)

    start_dt = parse_datetime(placed_start)
    end_dt = parse_datetime(placed_end) if placed_end else None
    # Make the datetimes timezone-aware so they get stored consistently with
    # smart-planner-placed events (otherwise Django emits a warning and the
    # interpretation is ambiguous).
    if start_dt is not None and is_naive(start_dt):
        start_dt = make_aware(start_dt)
    if end_dt is not None and is_naive(end_dt):
        end_dt = make_aware(end_dt)

    # Server-side constraint check — frontend also enforces these but never trust the client.
    err = _validate_placement(instance.event, start_dt, end_dt)
    if err:
        return JsonResponse({'error': err}, status=400)

    instance.placed_start = start_dt
    instance.placed_end = end_dt

    instance.status = ScheduleEvent.Status.SCHEDULED
    # Record who placed it — dashboard + completed views filter by this.
    instance.placed_by = request.user
    instance.save()
    return JsonResponse({'ok': True})
