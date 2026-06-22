from datetime import time as time_cls
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from student_calendar.forms import CreateEvent
from student_calendar.models import Event
from student_calendar.models.schedule_event import ScheduleEvent
from student_calendar.models.user_schedule import UserSchedule
from student_calendar.models.schedule import Schedule
from student_calendar.views.create_event import count_repeat_days

SENTINEL_YEAR = 1970


@login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)

    if request.method == "POST":
        form = CreateEvent(request.POST, instance=event, user=request.user)
        if form.is_valid():
            updated_event = form.save(commit=False)
            days_count = count_repeat_days(updated_event.repeat_days, updated_event.number_of_days)
            weeks_count = updated_event.repeat_weeks if updated_event.repeat_weeks else 1
            updated_event.max_instances = days_count * weeks_count
            updated_event.save()

            # Regenerate instances to match the new repeat schedule
            ScheduleEvent.objects.filter(event=updated_event).delete()
            user_schedule = UserSchedule.objects.filter(user=request.user).first()
            if not user_schedule:
                schedule = Schedule.objects.create(
                    title=f"{request.user.username}'s Schedule",
                    is_active=True
                )
                user_schedule = UserSchedule.objects.create(user=request.user, schedule=schedule)

            instances = [
                ScheduleEvent(
                    event=updated_event,
                    schedule=user_schedule.schedule,
                    status=ScheduleEvent.Status.CREATED,
                    occurrence_index=i + 1,
                    placed_start=None,
                    placed_end=None,
                    placed_by=request.user
                )
                for i in range(updated_event.max_instances)
            ]
            ScheduleEvent.objects.bulk_create(instances)
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    form = CreateEvent(instance=event, user=request.user)
    is_time_only = bool(event.start and event.end and event.start.year == SENTINEL_YEAR)

    if event.start:
        if is_time_only:
            # Case 5: read raw UTC hour/minute (equals user's intended time)
            form.fields['start_time'].initial = time_cls(event.start.hour, event.start.minute)
        else:
            local_start = timezone.localtime(event.start) if timezone.is_aware(event.start) else event.start
            form.fields['start_date'].initial = local_start.date()
            form.fields['start_time'].initial = local_start.time()

    if event.end:
        if is_time_only:
            form.fields['end_time'].initial = time_cls(event.end.hour, event.end.minute)
        else:
            local_end = timezone.localtime(event.end) if timezone.is_aware(event.end) else event.end
            form.fields['end_date'].initial = local_end.date()
            form.fields['end_time'].initial = local_end.time()

    if event.start and event.end:
        dur_mins = max(1, int((event.end - event.start).total_seconds() / 60))
        form.fields['hours'].initial = dur_mins // 60
        form.fields['minutes'].initial = dur_mins % 60
    elif event.duration:
        form.fields['hours'].initial = event.duration // 60
        form.fields['minutes'].initial = event.duration % 60

    selected_days = [bit for bit, _ in event.DAY_MAP if event.repeat_days & bit]
    return render(request, "partials/edit_event_form.html", {"form": form, "event": event, "selected_days": selected_days})
