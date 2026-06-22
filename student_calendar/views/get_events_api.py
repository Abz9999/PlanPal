import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from student_calendar.models import Event
from student_calendar.models.schedule_event import ScheduleEvent
from student_calendar.models.user_schedule import UserSchedule

SENTINEL_YEAR = 1970


@login_required
def get_events_api(request):
    active_schedule_id = UserSchedule.objects.filter(
        user=request.user, schedule__is_active=True
    ).values_list('schedule', flat=True).first()
    if not active_schedule_id:
        active_schedule_id = UserSchedule.objects.filter(
            user=request.user
        ).values_list('schedule', flat=True).first()

    schedule_events = ScheduleEvent.objects.filter(
        schedule=active_schedule_id
    ).select_related('event', 'event__category') if active_schedule_id else ScheduleEvent.objects.none()

    filters = request.GET.getlist("filter", "all")
    if filters != "all":
        schedule_events = schedule_events.filter(event__category__name__in=filters)

    data = []
    for se in schedule_events:
        data.append({
            'id': se.id,
            'event_id': se.event_id,
            'placed_start': se.placed_start.isoformat() if se.placed_start else None,
            'placed_end': se.placed_end.isoformat() if se.placed_end else None,
            'status': se.status,
            'occurrence_index': se.occurrence_index,
        })
    return JsonResponse(data, safe=False)


@login_required
def get_event_templates(request):
    events = Event.objects.filter(user=request.user).select_related('category')
    data = []
    for e in events:
        is_time_only = bool(e.start and e.end and e.start.year == SENTINEL_YEAR)

        if e.start and e.end:
            duration = max(1, int((e.end - e.start).total_seconds() / 60))
        else:
            duration = e.duration

        # Case 4: start set but end null -> JS treats as flexible
        has_start_time = not (e.start and not e.end)

        data.append({
            'id': e.id,
            'title': e.title,
            'start': e.start.isoformat() if (e.start and not is_time_only) else None,
            'end': e.end.isoformat() if (e.end and not is_time_only) else None,
            'duration': duration,
            'has_start_time': has_start_time,
            # Case 5: raw hour/minute bypass timezone conversion
            'constrained_hour': e.start.hour if is_time_only else None,
            'constrained_minute': e.start.minute if is_time_only else None,
            'category': e.category.name if e.category else '',
            'category_colour': e.category.colour if e.category else '#888888',
            'location': e.location or '',
            'description': e.description or '',
            'importance': e.get_importance_display(),
            'importance_num': e.importance,
            # Fields needed by old add-event.js for repeat/occurrence logic
            'repeat_days': e.repeat_days,
            'number_of_days': e.number_of_days,
            'repeat_days_display': e.get_repeat_days_display(),
        })
    return JsonResponse(data, safe=False)
