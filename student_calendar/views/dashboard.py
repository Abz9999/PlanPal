# Khan
# added annotate_event_counters so each event card can show its counters
# counters are derived from scheduleevent rows - not stored in db

from django.core.exceptions import FieldError
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import render

from student_calendar.models import Event, ScheduleEvent, UserSchedule, Category
from student_calendar.helpers import annotate_event_counters
import datetime

EVENTS_PER_PAGE = 30

@login_required
def dashboard(request):
    page = request.GET.get('page', 1)
    query = request.GET.get('query', '')

    categories = Category.objects.all().order_by('id')

    filters = request.GET.getlist('filter', 'all')

    events = Event.objects.filter(user=request.user)

    if filters != 'all':
        events = events.filter(category__name__in=filters)

    # attach the 4 counters to each event so the template can use them
    # e.g event.scheduled_count, event.completed_count etc
    events = annotate_event_counters(events)

    # sort events according to sort parameter
    events = sort_events(request, events)

    # filter events according to the query
    if query != '':
        events = events.filter(Q(title__icontains=query))

    paginator = Paginator(events, EVENTS_PER_PAGE)

    events_page = paginator.get_page(page)

    return render(
        request,
        "dashboard.html",
        {
            'events': events_page,
            'page_number': page,
            'categories': categories,
            'filters': filters
        }
    )

def sort_events(request, events):
    """ Function to filter events according to sort options as defined in url parameters. Returns sorted events queryset."""
    sort = request.GET.get('sort', 'title')

    # make sort parameter case-insensitive
    sort = sort.lower()

    if sort in ['amount_placed', '-amount_placed', 'next_scheduled']:
        # retrieve all events that are assigned to schedules that are assigned to user
        user_schedules = UserSchedule.objects.filter(user=request.user).values_list('schedule', flat=True)
        schedule_events = (ScheduleEvent.objects
                           .filter(schedule__in=user_schedules)
                           .exclude(status=ScheduleEvent.Status.CREATED)  # exclude non scheduled events
                           )
        if sort == 'next_scheduled':
            schedule_events = schedule_events.filter(placed_start__gte=datetime.datetime.now())
            events = get_events_from_schedule_events(schedule_events)
            events.sort(key=lambda event:event.next_occurrence(schedule_events))
        else:
            events = get_events_from_schedule_events(schedule_events)
            events.sort(key=lambda event: event.scheduled_occurrences(schedule_events), reverse=(sort[0] != '-'))
    else:
        # try catch to stop user entering bad data in url bar
        try:
            events = events.order_by(sort)

            # reversing order if sorting by importance
            if 'importance' in sort:
                events = events.reverse()

        except FieldError:
            events = events.order_by(Lower('title'))

    return events

def get_events_from_schedule_events(schedule_events):
    schedule_event_pks = list(schedule_events.values_list('event', flat=True))
    events = Event.objects.filter(pk__in=schedule_event_pks)
    events = list(events)
    return events