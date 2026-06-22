#main_page_view.py
from datetime import date, timedelta
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from student_calendar.models import Event, Schedule, ScheduleEvent, UserSchedule, Category
from django.views.decorators.csrf import csrf_exempt

SENTINEL_YEAR = 1970

def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def _prev_page(type, week_start):
    if type == 'day':
        return week_start - timedelta(days=1)
    if type == 'week':
        return week_start - timedelta(days=7)
    elif type == 'month':
        this_months_first = week_start.replace(day=1)
        prev_months_last = this_months_first - timedelta(days=1)
        return week_start - timedelta(days=prev_months_last.day)

    return week_start

def _next_page(type, week_start):
    if type == 'day':
        return week_start + timedelta(days=1)
    if type == 'week':
        return week_start + timedelta(days=7)
    elif type == 'month':
        next_months_first = (week_start.replace(day=1) + timedelta(days=31)).replace(day=1)
        this_months_last = next_months_first - timedelta(days=1)
        return week_start + timedelta(days=this_months_last.day)

    return week_start


@login_required
def main_page(request):
    """Renders the main page, using the given url parameters.

    Parameters:
        week: The first date of the current week
        filter: A list of selected categories used to filter the events displayed
        type: The type of calendar to display, a choice between DAY, WEEK or MONTH
        schedule: The user's active schedule
    """
    week_param     = request.GET.get("week")
    filter_param   = request.GET.getlist("filter", ["all"])
    calendar_type  = request.GET.get("type", "week")
    schedule_param = request.GET.get("schedule")

    context = {}
    addParamsToContext(request.user, filter_param, calendar_type, schedule_param, context)
    addDatesToContext(week_param, context)
    addEventsToContext(context)

    return render(request, 'main_page.html', context)


def addParamsToContext(user, filter_param, calendar_type, schedule_param, context):
    #Add the values given in the request directly to the context
    filter_options = Category.objects.all().order_by('id')

    context["user"] = user
    context["filter"] = filter_param
    context["filter_options"] = filter_options
    context["type"] = calendar_type
    context["schedule"] = schedule_param

    return context

def addDatesToContext(week_param, context):
    #Get the monday of the given week, and the previous and next weeks
    chosen_date = parse_date(week_param) if week_param else date.today()
    if chosen_date is None:
        chosen_date = date.today()

    week_start = chosen_date if context["type"] == 'day' else _week_start(chosen_date)
    context["week_start"]  = week_start
    context["prev_page"] = _prev_page(context["type"], week_start)
    context["next_page"]  = _next_page(context["type"], week_start)

    return context

def addEventsToContext(context):
    #Add the relevant event instances to the context
    qs = get_queryset(context)
    ordered_qs = qs.order_by("placed_start")
    events_data = format_events_data(ordered_qs)
    context["events"] = ordered_qs
    context["events_json"] = json.dumps(events_data)

    return context

def get_queryset(context):
    #Find the active or selected schedule belonging to this user
    user_schedule_ids = UserSchedule.objects.filter(user=context["user"]).values_list('schedule', flat=True)
    user_schedule_ids = filter_schedules(user_schedule_ids, context["schedule"], context["user"])
    week_end   = context["week_start"] + timedelta(days=1 if context["type"] == 'day' else 7)

    # Include SCHEDULED, COMPLETED, and MISSED instances so the user can see
    # what they've done on the calendar (greyed out via CSS classes added
    # in week-calendar.js). CREATED instances are excluded naturally
    # because placed_start is null for them.
    qs = ScheduleEvent.objects.filter(
        schedule__in=user_schedule_ids,
        placed_start__date__gte=context["week_start"],
        placed_start__date__lt=week_end,
    ).exclude(status=ScheduleEvent.Status.CREATED)

    if context["filter"] != ["all"]:
        qs = qs.filter(event__category__name__in=context["filter"])

    return qs

def filter_schedules(user_schedule_ids, schedule_param, req_user):
    try:
        selected_id = int(schedule_param)
    except:
        selected_id = None
    #Return the selected schedule, otherwise return the active schedule
    if selected_id and selected_id in user_schedule_ids:
        Schedule.objects.filter(userschedule__user=req_user).update(is_active=False)
        Schedule.objects.filter(id=selected_id).update(is_active=True)
        return [selected_id]
    else:
        active = UserSchedule.objects.filter(
            user=req_user, schedule__is_active=True
        ).values_list('schedule', flat=True).first()
        if active:
            return [active]

    return user_schedule_ids

def format_events_data(ordered_qs):
    events_data = []
    for se in ordered_qs:
        events_data.append({
            "id":           se.id,
            "title":        se.event.title,
            "category":     se.event.category.name if se.event.category else "",
            "colour":       se.event.category.colour if se.event.category else "#888888",
            "location":     se.event.location or "",
            "description":  se.event.description or "",
            "importance":   se.event.get_importance_display(),
            "importance_num": se.event.importance,
            "duration":       int((se.placed_end - se.placed_start).total_seconds() / 60)
                                  if se.placed_start and se.placed_end else None,
            "placed_start": se.placed_start.isoformat() if se.placed_start else None,
            "placed_end":   se.placed_end.isoformat()   if se.placed_end   else None,
            # Status drives the greyed-out / strikethrough styling for
            # completed and missed instances on the week-view grid.
            "status":       se.status,
        })

    return events_data


@login_required
def get_events(request):
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

        # Case 4: start set but end null → JS treats as flexible
        has_start_time = not (e.start and not e.end)

        data.append({
            'id': e.id,
            'title': e.title,
            'start': e.start.isoformat() if (e.start and not is_time_only) else None,
            'end': e.end.isoformat() if (e.end and not is_time_only) else None,
            'duration': duration,
            'has_start_time': has_start_time,
            # Case 5: raw hour/minute bypass timezone conversion
            'constrained_hour':   e.start.hour   if is_time_only else None,
            'constrained_minute': e.start.minute if is_time_only else None,
            'category': e.category.name if e.category else '',
            'category_colour': e.category.colour if e.category else '#888888',
            'location': e.location or '',
            'description': e.description or '',
            'importance': e.get_importance_display(),
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
def update_schedule_event(request, pk):
    data = json.loads(request.body)
    placed_start = data.get("new_placed_start")
    if placed_start in ("null", "", None):
        placed_start = None
    ScheduleEvent.objects.filter(pk=pk).update(placed_start=placed_start)
    ScheduleEvent.objects.filter(pk=pk).update(status=data["new_status"])
    return JsonResponse({"ok": True})
