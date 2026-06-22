# Modified by Khan

# create_event.py

from django.shortcuts import render, redirect
from student_calendar.forms import CreateEvent
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta

from student_calendar.models.schedule_event import ScheduleEvent
from student_calendar.models.user_schedule import UserSchedule
from student_calendar.models.schedule import Schedule
from student_calendar.models.event import Event

# works out how many days are selected from the repeat_days bitmask
# e.g. if Mon + Wed + Fri are selected, repeat_days = 21 (binary 0010101), so 3 days
def count_repeat_days(repeat_days, number_of_days):
    if not repeat_days:
        return number_of_days
    return bin(repeat_days).count("1")


def get_or_create_user_schedule(user):
    # get the users active schedule so we can link instances to it
    # if no schedule exists yet, create one automatically on first use
    user_schedule = UserSchedule.objects.filter(user=user, schedule__is_active=True).first()
    if not user_schedule:
        schedule = Schedule.objects.create(
            title=f"{user.username}'s Schedule",
            is_active=True
        )
        user_schedule = UserSchedule.objects.create(user=user, schedule=schedule)
    return user_schedule


def build_schedule_instances(event, user_schedule, user, weeks_count):
    repeat_days = event.repeat_days
    mapping = [
        (Event.MON, 0),
        (Event.TUE, 1),
        (Event.WED, 2),
        (Event.THU, 3),
        (Event.FRI, 4),
        (Event.SAT, 5),
        (Event.SUN, 6),
    ]
    repeat_weekdays = [weekday for mask, weekday in mapping if repeat_days & mask]
    base_date = timezone.now().date()
    return (
        build_repeating_instances(event, user_schedule, user, weeks_count, repeat_weekdays, base_date)
        if repeat_weekdays
        else build_default_instances(event, user_schedule, user)
    )


def build_repeating_instances(event, user_schedule, user, weeks_count, repeat_weekdays, base_date):
    instances = []
    occurrence_index = 1
    for week in range(weeks_count):
        for weekday in repeat_weekdays:
            day_offset = (weekday - base_date.weekday()) % 7
            occurrence_date = base_date + timedelta(days=day_offset) + timedelta(weeks=week)
            placed_start, placed_end = get_occurrence_datetimes(event, occurrence_date)
            instances.append(
                ScheduleEvent(
                    event=event,
                    schedule=user_schedule.schedule,
                    status=ScheduleEvent.Status.CREATED,
                    occurrence_index=occurrence_index,
                    placed_start=placed_start,
                    placed_end=placed_end,
                    placed_by=user
                )
            )
            occurrence_index += 1
    return instances


def build_default_instances(event, user_schedule, user):
    instances = []
    occurrence_index = 1
    for _ in range(event.max_instances):
        instances.append(
            ScheduleEvent(
                event=event,
                schedule=user_schedule.schedule,
                status=ScheduleEvent.Status.CREATED,
                occurrence_index=occurrence_index,
                placed_start=None,
                placed_end=None,
                placed_by=user
            )
        )
        occurrence_index += 1
    return instances


def get_occurrence_datetimes(event, occurrence_date):
    placed_start = None
    placed_end = None
    if event.start:
        start = timezone.make_aware(event.start) if timezone.is_naive(event.start) else event.start
        local_start = timezone.localtime(start)
        placed_start = timezone.make_aware(
            datetime.combine(occurrence_date, local_start.time())
        )
        if event.end:
            end = timezone.make_aware(event.end) if timezone.is_naive(event.end) else event.end
            local_end = timezone.localtime(end)
            placed_end = timezone.make_aware(
                datetime.combine(occurrence_date, local_end.time())
            )
    return placed_start, placed_end


@login_required
def create_event(request):
    # determine where to redirect back to
    next_url = request.POST.get("next") or request.GET.get("next") or "main_page"
    if request.method == "POST":
        form = CreateEvent(request.POST, user=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user  # ensure user is set

            # work out how many total instances this event template will have
            # max_instances = number of selected days * number of weeks
            days_count = count_repeat_days(event.repeat_days, event.number_of_days)
            weeks_count = event.repeat_weeks if event.repeat_weeks else 1
            event.max_instances = days_count * weeks_count
            event.save()

            user_schedule = get_or_create_user_schedule(request.user)
            if user_schedule:
                instances = build_schedule_instances(event, user_schedule, request.user, weeks_count)
                ScheduleEvent.objects.bulk_create(instances)
            return redirect(next_url)
    else:
        form = CreateEvent(user=request.user)
    return render(request, "partials/create_event.html", {"form": form, "next": next_url})
