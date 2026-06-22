# Ashrith - Statistics service
from datetime import timedelta
from django.utils import timezone
from collections import defaultdict
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from student_calendar.models import ScheduleEvent, Event


VALID_PERIODS = {"week", "month", "all"}


def normalise_period(period_param):
    if period_param in VALID_PERIODS:
        return period_param
    return "all"

def resolve_period(period_param):
    """Resolve a period string into an inclusive date range."""

    period = normalise_period(period_param)
    today = timezone.localdate()

    if period == "week":
        return _resolve_week_period(today)

    if period == "month":
        return _resolve_month_period(today)

    return (None, None)

def get_category_breakdown(user, start_date, end_date):
    """Return category workload and completion data for the selected period."""
    queryset = _get_category_schedule_events(user, start_date, end_date)
    grouped_categories = _group_category_stats(queryset)

    return _build_category_breakdown(grouped_categories)

def get_hero_stats(user):
    """Return the top-level statistics shown in the hero section."""    
    base_queryset = _get_user_schedule_events(user)

    return {
        "total_completed": _get_total_completed(base_queryset),
        "longest_active_streak": _get_longest_active_streak(base_queryset),
        "hours_this_month": _get_hours_scheduled_this_month(base_queryset),
        **_get_completion_metrics(base_queryset),
    }

def get_weekly_heatmap(user, start_date, end_date):
    """Return week rows of completion counts grouped by placed end date."""
    queryset = _get_heatmap_schedule_events(user, start_date, end_date)
    completions_by_day = _group_heatmap_counts_by_day(queryset)

    if not completions_by_day:
        return []

    return _build_heatmap_weeks(completions_by_day)

def get_streak_for_template(event):
    """Return the current completed streak for a template."""
    resolved_instances = _get_resolved_template_instances(event)
    return _count_current_template_streak(resolved_instances)


def get_streak_leaderboard(user, limit=10):
    """Return the user's top active template streaks in descending order."""
    templates = _get_user_templates(user)
    leaderboard_rows = _build_streak_rows(templates)
    leaderboard_rows.sort(key=_get_streak_sort_key, reverse=True)

    return leaderboard_rows[:limit]

def get_weekly_trends(user, num_weeks=12):
    """Return weekly completion rate and hours for the most recent weeks."""
    current_monday = _get_current_monday()
    trend_rows = []

    for week_offset in range(num_weeks - 1, -1, -1):
        week_start = current_monday - timedelta(weeks=week_offset)
        trend_rows.append(_build_weekly_trend_row(user, week_start))

    return trend_rows

def _resolve_week_period(today):
    """Return the Monday-Sunday range for the current week."""
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)
    return (start_date, end_date)

def _resolve_month_period(today):
    """Return the first and last day of the current month."""
    start_date = today.replace(day=1)
    end_date = _get_month_end_date(start_date)
    return (start_date, end_date)

def _get_month_end_date(start_date):
    """Return the final day of the month for the provided date."""
    if start_date.month == 12:
        next_month = start_date.replace(year=start_date.year + 1, month=1)
        return next_month - timedelta(days=1)

    next_month = start_date.replace(month=start_date.month + 1)
    return next_month - timedelta(days=1)


def _get_user_schedule_events(user):
    return ScheduleEvent.objects.filter(placed_by=user).select_related("event")


def _get_total_completed(queryset):
    return queryset.filter(status=ScheduleEvent.Status.COMPLETED).count()


def _get_completion_metrics(queryset):
    """percentage completion"""
    resolved_count = _get_resolved_count(queryset)
    completed_count = _get_total_completed(queryset)
    completion_percentage = _calculate_completion_percentage(
        completed_count,
        resolved_count,
    )

    return {
        "completion_pct": completion_percentage,
        "pct_band": _get_completion_band(completion_percentage),
    }


def _get_resolved_count(queryset):
    """not considering events that have been scheduled or created"""
    resolved_statuses = [
        ScheduleEvent.Status.COMPLETED,
        ScheduleEvent.Status.MISSED,
    ]
    return queryset.filter(status__in=resolved_statuses).count()


def _calculate_completion_percentage(completed_count, resolved_count):
    if resolved_count == 0:
        return 0

    return round((completed_count / resolved_count) * 100)


def _get_completion_band(completion_percentage):
    if completion_percentage >= 90:
        return "gold"

    if completion_percentage >= 75:
        return "green"

    if completion_percentage >= 50:
        return "amber"

    return "red"


def _get_hours_scheduled_this_month(queryset):
    month_start_date = timezone.localdate().replace(day=1)
    month_queryset = _filter_events_for_current_month(queryset, month_start_date)
    total_minutes = _get_total_minutes(month_queryset)

    return round(total_minutes / 60, 1)


def _filter_events_for_current_month(queryset, month_start_date):
    """Include only month-to-date placed events that contribute to workload hours."""
    active_statuses = [
        ScheduleEvent.Status.SCHEDULED,
        ScheduleEvent.Status.COMPLETED,
    ]
    return queryset.filter(
        status__in=active_statuses,
        placed_start__date__gte=month_start_date,
        placed_end__isnull=False,
    ).exclude(placed_start__isnull=True)


def _get_total_minutes(queryset):
    total_duration = queryset.aggregate(
        total_duration=Coalesce(Sum(F("placed_end") - F("placed_start")), timedelta()),
    )["total_duration"]

    return int(total_duration.total_seconds() // 60)


def _get_longest_active_streak(queryset):
    """Return the best current completed streak across all event templates."""
    grouped_events = _group_events_by_template(queryset)
    streak_lengths = _get_streak_lengths(grouped_events)

    if not streak_lengths:
        return 0

    return max(streak_lengths)


def _group_events_by_template(queryset):
    """Group schedule events per template so streaks are calculated independently."""
    ordered_events = queryset.order_by("event_id", "occurrence_index", "placed_start", "id")
    grouped_events = defaultdict(list)

    for schedule_event in ordered_events:
        grouped_events[schedule_event.event_id].append(schedule_event)

    return grouped_events


def _get_streak_lengths(grouped_events):
    return [
        _get_template_active_streak(schedule_events)
        for schedule_events in grouped_events.values()
    ]


def _get_template_active_streak(schedule_events):
    """counts backwards from the current instance to find the current streak"""
    streak_length = 0

    for schedule_event in reversed(schedule_events):
        if schedule_event.status != ScheduleEvent.Status.COMPLETED:
            break
        streak_length += 1

    return streak_length

def _get_category_schedule_events(user, start_date, end_date):
    """scheduled events loaded with category and filtered for the range."""
    queryset = ScheduleEvent.objects.filter(
        placed_by=user,
        placed_start__isnull=False,
        placed_end__isnull=False,
    ).select_related("event__category")

    if not start_date or not end_date:
        return queryset

    return queryset.filter(
        placed_start__date__gte=start_date,
        placed_start__date__lte=end_date,
    )


def _group_category_stats(queryset):
    """Aggregate duration and outcome counts per category."""
    grouped_categories = defaultdict(_build_empty_category_stats)

    for schedule_event in queryset:
        category = schedule_event.event.category
        category_stats = grouped_categories[category.id]

        _set_category_identity(category_stats, category)
        _add_category_minutes(category_stats, schedule_event)
        _add_category_outcome(category_stats, schedule_event.status)

    return grouped_categories


def _build_empty_category_stats():
    return {
        "name": "",
        "colour": "#888888",
        "minutes": 0,
        "completed": 0,
        "resolved": 0,
    }


def _set_category_identity(category_stats, category):
    category_stats["name"] = category.name
    category_stats["colour"] = category.colour


def _add_category_minutes(category_stats, schedule_event):
    active_statuses = {
        ScheduleEvent.Status.SCHEDULED,
        ScheduleEvent.Status.COMPLETED,
    }
    if schedule_event.status not in active_statuses:
        return

    duration_minutes = _get_schedule_event_minutes(schedule_event)
    category_stats["minutes"] += duration_minutes


def _get_schedule_event_minutes(schedule_event):
    """minute conversion"""
    duration = schedule_event.placed_end - schedule_event.placed_start
    return int(duration.total_seconds() // 60)


def _add_category_outcome(category_stats, status):
    if status == ScheduleEvent.Status.COMPLETED:
        category_stats["completed"] += 1
        category_stats["resolved"] += 1
        return

    if status == ScheduleEvent.Status.MISSED:
        category_stats["resolved"] += 1


def _build_category_breakdown(grouped_categories):
    """convert grouped data into category rows."""
    category_breakdown = [
        _finalise_category_stats(category_stats)
        for category_stats in grouped_categories.values()
    ]
    category_breakdown.sort(key=_get_category_sort_key, reverse=True)

    return category_breakdown


def _finalise_category_stats(category_stats):
    hours = round(category_stats["minutes"] / 60, 1)
    completion_percentage = _calculate_completion_percentage(
        category_stats["completed"],
        category_stats["resolved"],
    )

    return {
        "name": category_stats["name"],
        "colour": category_stats["colour"],
        "hours": hours,
        "completion_pct": completion_percentage,
    }


def _get_category_sort_key(category_stats):
    return category_stats["hours"]

def _get_heatmap_schedule_events(user, start_date, end_date):
    queryset = ScheduleEvent.objects.filter(
        placed_by=user,
        status=ScheduleEvent.Status.COMPLETED,
        placed_end__isnull=False,
    )

    if not start_date or not end_date:
        return queryset

    return queryset.filter(
        placed_end__date__gte=start_date,
        placed_end__date__lte=end_date,
    )


def _group_heatmap_counts_by_day(queryset):
    """Count completions per day for the heatmap grid."""
    completions_by_day = defaultdict(int)

    for schedule_event in queryset:
        completions_by_day[schedule_event.placed_end.date()] += 1

    return completions_by_day


def _build_heatmap_weeks(completions_by_day):
    """Build complete weekday rows so the heatmap grid has no gaps."""
    earliest_date = min(completions_by_day)
    latest_date = max(completions_by_day)
    current_week_start = _get_week_start(earliest_date)
    week_rows = []

    while current_week_start <= latest_date:
        week_rows.append(_build_heatmap_week_row(current_week_start, completions_by_day))
        current_week_start += timedelta(days=7)

    return week_rows


def _get_week_start(day):
    return day - timedelta(days=day.weekday())


def _build_heatmap_week_row(week_start, completions_by_day):
    """Create one week row with seven daily counts and a stable intensity max."""
    day_counts = _get_heatmap_day_counts(week_start, completions_by_day)

    return {
        "week_start": week_start,
        "days": day_counts,
        "max": max(day_counts) or 1,
    }


def _get_heatmap_day_counts(week_start, completions_by_day):
    """Return weekday completion counts for one heatmap row."""
    day_counts = []

    for offset in range(7):
        current_day = week_start + timedelta(days=offset)
        day_counts.append(completions_by_day.get(current_day, 0))

    return day_counts

def _get_resolved_template_instances(event):
    """Use only resolved instances because scheduled and created do not affect streaks."""
    resolved_statuses = [
        ScheduleEvent.Status.COMPLETED,
        ScheduleEvent.Status.MISSED,
    ]
    return ScheduleEvent.objects.filter(
        event=event,
        placed_end__isnull=False,
        status__in=resolved_statuses,
    ).order_by("-placed_end", "-id")


def _count_current_template_streak(resolved_instances):
    """Count instances completed until an instance is missed"""
    streak_count = 0

    for resolved_instance in resolved_instances:
        if resolved_instance.status != ScheduleEvent.Status.COMPLETED:
            break
        streak_count += 1

    return streak_count


def _get_user_templates(user):
    return Event.objects.filter(user=user)


def _build_streak_rows(templates):
    """rows for any template with active streaks are built here"""
    leaderboard_rows = []

    for template in templates: 
        streak_count = get_streak_for_template(template)
        if streak_count == 0:
            continue

        leaderboard_rows.append(
            {
                "title": template.title,
                "streak": streak_count,
                "event_id": template.id,
            }
        )

    return leaderboard_rows


def _get_streak_sort_key(streak_row):
    return streak_row["streak"]

def _get_current_monday():
    today = timezone.localdate()
    return today - timedelta(days=today.weekday())


def _build_weekly_trend_row(user, week_start):
    """trend row for completion percentage and hours for a week"""
    week_end = week_start + timedelta(days=6)
    week_queryset = _get_weekly_trend_queryset(user, week_start, week_end)

    return {
        "label": week_start.strftime("%d %b"),
        "completion_pct": _get_weekly_completion_percentage(week_queryset),
        "hours": _get_weekly_scheduled_hours(week_queryset),
    }


def _get_weekly_trend_queryset(user, week_start, week_end):
    """placed events for a week loaded for trend calculation"""
    return ScheduleEvent.objects.filter(
        placed_by=user,
        placed_start__date__gte=week_start,
        placed_start__date__lte=week_end,
        placed_start__isnull=False,
        placed_end__isnull=False,
    )


def _get_weekly_completion_percentage(queryset):
    completed_count = queryset.filter(
        status=ScheduleEvent.Status.COMPLETED,
    ).count()
    resolved_count = queryset.filter(
        status__in=[
            ScheduleEvent.Status.COMPLETED,
            ScheduleEvent.Status.MISSED,
        ],
    ).count()

    return _calculate_completion_percentage(completed_count, resolved_count)


def _get_weekly_scheduled_hours(queryset):
    active_queryset = queryset.filter(
        status__in=[
            ScheduleEvent.Status.SCHEDULED,
            ScheduleEvent.Status.COMPLETED,
        ],
    )
    total_minutes = _get_total_minutes(active_queryset)

    return round(total_minutes / 60, 1)