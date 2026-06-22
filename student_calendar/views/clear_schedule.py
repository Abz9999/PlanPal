# Created by Ashrith
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from student_calendar.models import ScheduleEvent, Schedule, UserSchedule


@login_required
def clear_schedule(request, schedule_id=None):
    """
    Clear all scheduled events from the user's calendar by resetting
    their status to CREATED instead of deleting them.
    This does not affect the Event objects themselves (dashboard tasks remain).
    """
    if request.method == "POST":

        # If no schedule_id, pick first schedule
        if schedule_id is None:
            schedule = UserSchedule.objects.filter(user=request.user, schedule__is_active=True).first()
            if not schedule:
                return redirect("main_page")
            schedule = schedule.schedule
        else:
            schedule = get_object_or_404(Schedule, id=schedule_id)

        # Ensure the user actually owns this schedule
        if not UserSchedule.objects.filter(
            user=request.user,
            schedule=schedule
        ).exists():
            return redirect("main_page")

        # Reset scheduled events back to CREATED and wipe their placement
        # so the month view + any other code that reads placed_start doesn't
        # show ghost events after the schedule has been cleared.
        with transaction.atomic():
            ScheduleEvent.objects.filter(
                schedule=schedule,
                status=ScheduleEvent.Status.SCHEDULED
            ).update(
                status=ScheduleEvent.Status.CREATED,
                placed_start=None,
                placed_end=None,
            )

    # Redirect back to main page
    return redirect("main_page")