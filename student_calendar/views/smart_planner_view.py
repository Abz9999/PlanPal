# Khan - smart_planner_view.py
# This is the backend view for the Smart Planner feature.
# Right now it just has one endpoint that returns all the user's
# event templates as JSON so Step 2 of the popup can display them.

import json
from datetime import date, time as time_cls

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware

from student_calendar.helpers import annotate_event_counters
from student_calendar.models import ScheduleEvent
from student_calendar.models.event import Event
from student_calendar.smart_planner_service import run_smart_planner

@login_required
def get_smart_planner_events(request):
    """
    Khan - GET /smart-plan/events/
    Returns all event templates for the logged-in user as JSON.
    Each event includes its category info and all 4 status counters
    (created/scheduled/completed/missed) so the JS can display them.
    """

    # Khan - Grab all events belonging to this user, join in category so we
    # don't hit the database again for each event's category name/colour
    events_qs = Event.objects.filter(
        user=request.user
    ).select_related('category').order_by('title')

    # Khan - annotate_event_counters adds created_count, scheduled_count,
    # completed_count, missed_count to each event in the queryset
    events_qs = annotate_event_counters(events_qs)

    # Khan - Build the list of dicts that will be sent back as JSON
    events_data = []
    for event in events_qs:

        # Khan - Work out the actual duration in minutes for this event.
        # Flexible events store duration directly on the model.
        # Fixed events don't have a duration field - we derive it from start and end.
        if event.duration:
            # Khan - Flexible event: duration is already stored in minutes
            duration_minutes = event.duration
            is_fixed         = False
            duration_display = event.duration_format()

        elif event.start and event.end:
            # Khan - Fixed event: calculate duration from the start/end datetimes
            duration_minutes = int((event.end - event.start).total_seconds() / 60)
            is_fixed         = True

            # Khan - Build a readable display string e.g. "1 hr · Fixed" or "45 mins · Fixed"
            h = duration_minutes // 60
            m = duration_minutes % 60
            if h > 0 and m > 0:
                duration_display = f"{h} hr{'s' if h > 1 else ''} {m} mins \u00b7 Fixed"
            elif h > 0:
                duration_display = f"{h} hr{'s' if h > 1 else ''} \u00b7 Fixed"
            else:
                duration_display = f"{m} mins \u00b7 Fixed"

        else:
            # Khan - No duration info available at all (shouldn't happen but safe fallback)
            duration_minutes = None
            is_fixed         = False
            duration_display = None

        events_data.append({
            'id':               event.id,
            'title':            event.title,
            'importance':       event.importance,
            'duration':         event.duration,          # original field (null for fixed)
            'duration_minutes': duration_minutes,        # actual minutes for ALL event types
            'duration_display': duration_display,        # readable string for display
            'is_fixed':         is_fixed,                # True if this is a fixed-time event
            'repeat_days':      event.repeat_days,

            # Khan - Category fields (safe defaults if no category is set)
            'category_id':      event.category.id     if event.category else None,
            'category_name':    event.category.name   if event.category else 'Uncategorised',
            'category_colour':  event.category.colour if event.category else '#888888',

            # Khan - The 4 status counters added by annotate_event_counters
            'created_count':    event.created_count,
            'scheduled_count':  event.scheduled_count,
            'completed_count':  event.completed_count,
            'missed_count':     event.missed_count,
        })

    return JsonResponse({'events': events_data})


@login_required
def generate_smart_plan(request):
    """Run the smart planner algorithm with the given constraints and return a preview.

    Expects a POST body with JSON:
        {'constraints': {...}, 'selected_template_ids': [int, ...]}

    Returns JSON with the placement preview, or an error with HTTP 400/405/500.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)

    constraints = payload.get('constraints', {})
    event_ids = payload.get('selected_template_ids', [])

    missing = _missing_constraint_key(constraints)
    if missing:
        return JsonResponse({'error': f'Missing constraint field: {missing}'}, status=400)

    if not event_ids:
        return JsonResponse({'error': 'No event templates selected'}, status=400)

    error = _validate_constraint_values(constraints)
    if error:
        return JsonResponse({'error': error}, status=400)

    try:
        result = run_smart_planner(request.user, constraints, event_ids)
    except Exception as exc:
        return JsonResponse({'error': f'Planning failed: {exc}'}, status=500)

    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=400)

    return JsonResponse(result)


def _missing_constraint_key(constraints):
    """Return the name of the first required constraint key that is missing, or None."""
    required_keys = [
        'start_date', 'end_date', 'day_start', 'day_end',
        'buffer_minutes', 'selected_days_bitmask', 'keep_or_erase',
    ]
    for key in required_keys:
        if key not in constraints:
            return key
    return None


def _validate_constraint_values(constraints):
    """Validate constraint field values. Returns an error string, or None if valid."""
    if constraints.get('selected_days_bitmask', 0) == 0:
        return 'At least one active day must be selected'

    try:
        start = date.fromisoformat(constraints['start_date'])
        end = date.fromisoformat(constraints['end_date'])
    except (ValueError, TypeError):
        return 'Invalid date format'
    if end < start:
        return 'End date cannot be before start date'

    try:
        day_start = time_cls.fromisoformat(constraints['day_start'])
        day_end = time_cls.fromisoformat(constraints['day_end'])
    except (ValueError, TypeError):
        return 'Invalid time format'
    if day_start >= day_end:
        return 'Day start time must be before day end time'

    buffer_minutes = constraints.get('buffer_minutes', 0)
    if not isinstance(buffer_minutes, int) or buffer_minutes < 0 or buffer_minutes > 240:
        return 'Buffer minutes must be an integer between 0 and 240'

    return None

@login_required
def confirm_smart_plan(request):
    """Persist the approved plan to the database.

    Marks placed instances as SCHEDULED with their chosen times, and resets any
    previously-SCHEDULED instances that are in the unplaced list back to CREATED.
    The whole operation is atomic — on failure nothing persists.

    Expects a POST body with JSON:
        {'placed': [{'schedule_event_id': int, 'placed_start': str, 'placed_end': str}, ...],
         'unplaced': [{'schedule_event_id': int}, ...]}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)

    placed_items = payload.get('placed', [])
    unplaced_items = payload.get('unplaced', [])

    if not placed_items:
        return JsonResponse({'error': 'No placed instances to confirm'}, status=400)

    # Pre-validate: reject the whole request if any ID doesn't belong to this user
    all_ids = [
        item.get('schedule_event_id')
        for item in (placed_items + unplaced_items)
        if item.get('schedule_event_id')
    ]

    if all_ids:
        # Check ownership via Event.user — the direct and canonical owner path.
        # Using schedule -> userschedule -> user would over-count if a user
        # happens to have duplicate UserSchedule rows pointing at the same
        # Schedule (which can happen if the seeder is run multiple times).
        unique_ids = set(all_ids)
        owned_count = ScheduleEvent.objects.filter(
            id__in=unique_ids,
            event__user=request.user,
        ).count()
        if owned_count != len(unique_ids):
            return JsonResponse(
                {'error': 'Unauthorised: one or more event IDs do not belong to you'},
                status=403,
            )

    with transaction.atomic():
        # Mark each placed instance as SCHEDULED with its allocated times
        saved_count = 0
        for item in placed_items:
            event_id = item.get('schedule_event_id')
            start_str = item.get('placed_start')
            end_str = item.get('placed_end')

            if not event_id or not start_str or not end_str:
                continue

            placed_start = parse_datetime(start_str)
            placed_end = parse_datetime(end_str)

            if not placed_start or not placed_end:
                continue

            if is_naive(placed_start):
                placed_start = make_aware(placed_start)
            if is_naive(placed_end):
                placed_end = make_aware(placed_end)

            updated = ScheduleEvent.objects.filter(
                id=event_id,
                event__user=request.user,
            ).update(
                status=2,  # SCHEDULED
                placed_start=placed_start,
                placed_end=placed_end,
            )
            saved_count += updated

        # Reset any SCHEDULED instances that couldn't be placed back to CREATED
        for item in unplaced_items:
            event_id = item.get('schedule_event_id')
            if not event_id:
                continue

            ScheduleEvent.objects.filter(
                id=event_id,
                status=2,  # SCHEDULED
                event__user=request.user,
            ).update(
                status=1,  # CREATED
                placed_start=None,
                placed_end=None,
            )

    return JsonResponse({
        'success': True,
        'placed_count': saved_count,
    })