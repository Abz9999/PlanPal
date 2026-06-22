# Khan
# deletes an event template and all its instances
# ScheduleEvent rows are deleted automatically because the FK has on_delete=CASCADE

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from student_calendar.models import Event

@login_required
def delete_event(request, pk):
    if request.method == 'POST':
        # make sure the event belongs to this user before deleting
        event = get_object_or_404(Event, pk=pk, user=request.user)
        event.delete()
    return redirect('dashboard')
