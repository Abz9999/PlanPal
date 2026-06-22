# Created by Khan

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from student_calendar.models import ScheduleEvent, Event

@login_required
def completed_events(request):
    # Get distinct event IDs that have at least one completed instance for this user
    completed_event_ids = ScheduleEvent.objects.filter(status=ScheduleEvent.Status.COMPLETED, placed_by=request.user).values_list('event_id', flat=True).distinct()

    # For each unique event template, collect all its instances and a completed count.
    # total_count uses event.max_instances so the numbers match the dashboard
    # (avoids drift when old orphaned ScheduleEvent rows inflate the raw count).
    event_data = []
    for event in Event.objects.filter(id__in=completed_event_ids):
        instances = ScheduleEvent.objects.filter(event=event, placed_by=request.user)
        completed_count = instances.filter(status=ScheduleEvent.Status.COMPLETED).count()
        total_count = event.max_instances or instances.count()
        event_data.append({
            'event': event,
            'completed_count': completed_count,
            'total_count': total_count,
            'instances': instances,
            'modal_id': f'modal-{event.id}',
        })

    return render(request, 'completed_events.html', {'event_data': event_data})
