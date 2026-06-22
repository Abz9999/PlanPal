# Created by Theo
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from student_calendar.models import Event


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(
        request,
        'event_detail.html',
        {'event': event}
    )
