# Created by Khan

# helpers.py — Query-time utility functions for the student_calendar app.
# Counters are never stored in the database — they are always derived from
# ScheduleEvent rows at query time using Django ORM annotations.

from django.db.models import Count, Q
from student_calendar.models.schedule_event import ScheduleEvent


def annotate_event_counters(queryset):
    """
    Annotates an Event queryset with 4 derived counters, each counting
    ScheduleEvent rows by status for that specific event template.

    Usage:
        events = annotate_event_counters(Event.objects.filter(user=request.user))
        # Each event now has: event.created_count, event.scheduled_count,
        #                      event.completed_count, event.missed_count

    Example results:
        gym.created_count   = 3   (3 instances not yet placed)
        gym.scheduled_count = 6   (6 instances on the schedule)
        uni.completed_count = 7   (7 uni instances completed)
        uni.missed_count    = 1   (1 uni instance missed)
    """
    return queryset.annotate(

        # Count ScheduleEvent rows for this template where status = CREATED
        # Represents instances that exist but have not been placed on the schedule yet
        created_count=Count(
            'scheduleevent',
            filter=Q(scheduleevent__status=ScheduleEvent.Status.CREATED)
        ),

        # Count ScheduleEvent rows for this template where status = SCHEDULED
        # Represents instances currently placed on the calendar
        scheduled_count=Count(
            'scheduleevent',
            filter=Q(scheduleevent__status=ScheduleEvent.Status.SCHEDULED)
        ),

        # Count ScheduleEvent rows for this template where status = COMPLETED
        # Represents instances the user has marked as done
        completed_count=Count(
            'scheduleevent',
            filter=Q(scheduleevent__status=ScheduleEvent.Status.COMPLETED)
        ),

        # Count ScheduleEvent rows for this template where status = MISSED
        # Represents instances that passed their end time without being completed
        missed_count=Count(
            'scheduleevent',
            filter=Q(scheduleevent__status=ScheduleEvent.Status.MISSED)
        ),

        # Count ScheduleEvent rows for this template that have left the sidebar —
        # i.e. anything that was placed on the calendar at some point. Completing
        # or missing an instance does not "un-place" it, so those still count.
        # Dashboard cards use this so the X/Y counter only ever grows as the
        # user works through a template, rather than shrinking when they tick
        # instances off as completed.
        placed_count=Count(
            'scheduleevent',
            filter=Q(scheduleevent__status__in=[
                ScheduleEvent.Status.SCHEDULED,
                ScheduleEvent.Status.COMPLETED,
                ScheduleEvent.Status.MISSED,
            ])
        ),
    )
