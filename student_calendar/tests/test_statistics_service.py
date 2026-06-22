from datetime import date, datetime
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from student_calendar.models import ScheduleEvent, Category, Event, Schedule
from student_calendar import statistics_service


class NormalisePeriodTests(SimpleTestCase):
    def test_returns_same_value_for_supported_period(self):
        result = statistics_service.normalise_period("week")
        self.assertEqual(result, "week")

    def test_returns_all_for_invalid_period(self):
        result = statistics_service.normalise_period("invalid")
        self.assertEqual(result, "all")


class ResolvePeriodTests(SimpleTestCase):
    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_current_week_range_for_week_period(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 1)

        start_date, end_date = statistics_service.resolve_period("week")

        self.assertEqual(start_date, date(2026, 3, 30))
        self.assertEqual(end_date, date(2026, 4, 5))

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_current_month_range_for_month_period(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 2)

        start_date, end_date = statistics_service.resolve_period("month")

        self.assertEqual(start_date, date(2026, 4, 1))
        self.assertEqual(end_date, date(2026, 4, 30))

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_none_range_for_all_period(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 1)

        start_date, end_date = statistics_service.resolve_period("all")

        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_none_range_for_invalid_period(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 1)

        start_date, end_date = statistics_service.resolve_period("bad-value")

        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_december_month_end_correctly(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 12, 10)

        start_date, end_date = statistics_service.resolve_period("month")

        self.assertEqual(start_date, date(2026, 12, 1))
        self.assertEqual(end_date, date(2026, 12, 31))

class HeroStatsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls._create_user("stats-user")
        cls.other_user = cls._create_user("other-user")
        cls.category = Category.objects.create(name="Study", colour="#336699")
        cls.schedule = Schedule.objects.create(title="Main Schedule")
        cls.other_schedule = Schedule.objects.create(title="Other Schedule")
        cls.focus_event = cls._create_event("Focus")
        cls.gym_event = cls._create_event("Gym")
        cls.other_event = cls._create_event("Other")

    @classmethod
    def _create_user(cls, username):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
        )

    @classmethod
    def _create_event(cls, title):
        return Event.objects.create(
            title=title,
            category=cls.category,
            user=cls.user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )

    def test_returns_zero_values_when_user_has_no_schedule_events(self):
        empty_user = self._create_user("empty-user")

        hero = statistics_service.get_hero_stats(empty_user)

        self.assertEqual(hero["total_completed"], 0)
        self.assertEqual(hero["longest_active_streak"], 0)
        self.assertEqual(hero["hours_this_month"], 0.0)
        self.assertEqual(hero["completion_pct"], 0)
        self.assertEqual(hero["pct_band"], "red")

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_expected_completed_count(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 14)
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=1,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=2,
        )

        hero = statistics_service.get_hero_stats(self.user)

        self.assertEqual(hero["total_completed"], 2)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_expected_longest_active_streak(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 14)
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.MISSED,
            occurrence_index=1,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=2,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=3,
        )
        self._create_schedule_event(
            event=self.gym_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=1,
        )

        hero = statistics_service.get_hero_stats(self.user)

        self.assertEqual(hero["longest_active_streak"], 2)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_expected_hours_scheduled_this_month(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 14)
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.SCHEDULED,
            placed_start=self._aware_datetime(2026, 4, 3, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 3, 10, 30),
            occurrence_index=1,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 4, 10, 14, 0),
            placed_end=self._aware_datetime(2026, 4, 10, 15, 0),
            occurrence_index=2,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.MISSED,
            placed_start=self._aware_datetime(2026, 4, 11, 14, 0),
            placed_end=self._aware_datetime(2026, 4, 11, 15, 0),
            occurrence_index=3,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.SCHEDULED,
            placed_start=self._aware_datetime(2026, 3, 30, 14, 0),
            placed_end=self._aware_datetime(2026, 3, 30, 16, 0),
            occurrence_index=4,
        )

        hero = statistics_service.get_hero_stats(self.user)

        self.assertEqual(hero["hours_this_month"], 2.5)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_expected_completion_percentage_and_band(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 14)
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=1,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=2,
        )
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.MISSED,
            occurrence_index=3,
        )

        hero = statistics_service.get_hero_stats(self.user)

        self.assertEqual(hero["completion_pct"], 67)
        self.assertEqual(hero["pct_band"], "amber")

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_ignores_schedule_events_belonging_to_other_users(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 14)
        self._create_schedule_event(
            event=self.focus_event,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=1,
        )
        ScheduleEvent.objects.create(
            schedule=self.other_schedule,
            event=self.other_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.other_user,
            occurrence_index=1,
        )

        hero = statistics_service.get_hero_stats(self.user)

        self.assertEqual(hero["total_completed"], 1)

    def _create_schedule_event(
        self,
        event,
        status,
        occurrence_index,
        placed_start=None,
        placed_end=None,
    ):
        return ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=event,
            status=status,
            placed_by=self.user,
            occurrence_index=occurrence_index,
            placed_start=placed_start,
            placed_end=placed_end,
        )

    def _aware_datetime(self, year, month, day, hour, minute):
        naive_datetime = datetime(year, month, day, hour, minute)
        return timezone.make_aware(naive_datetime)

class CategoryBreakdownTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls._create_user("category-user")
        cls.other_user = cls._create_user("outside-user")
        cls.study_category = Category.objects.create(name="Cognitive Improvement", colour="#336699")
        cls.gym_category = Category.objects.create(name="Fitness", colour="#22aa66")
        cls.other_category = Category.objects.create(name="Self Improvement", colour="#aa3344")
        cls.schedule = Schedule.objects.create(title="Main Schedule")
        cls.other_schedule = Schedule.objects.create(title="Other Schedule")
        cls.study_event = cls._create_event("Revision", cls.study_category, cls.user)
        cls.gym_event = cls._create_event("Workout", cls.gym_category, cls.user)
        cls.other_event = cls._create_event("Outside", cls.other_category, cls.other_user)

    @classmethod
    def _create_user(cls, username):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
        )

    @classmethod
    def _create_event(cls, title, category, user):
        return Event.objects.create(
            title=title,
            category=category,
            user=user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )

    def test_returns_empty_list_when_user_has_no_category_events(self):
        breakdown = statistics_service.get_category_breakdown(self.user, None, None)

        self.assertEqual(breakdown, [])

    def test_returns_sorted_category_hours_and_completion_rates(self):
        self._create_schedule_event(
            event=self.study_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 4, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 10, 11, 0),
        )
        self._create_schedule_event(
            event=self.study_event,
            status=ScheduleEvent.Status.MISSED,
            placed_start=self._aware_datetime(2026, 4, 12, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 12, 10, 0),
        )
        self._create_schedule_event(
            event=self.gym_event,
            status=ScheduleEvent.Status.SCHEDULED,
            placed_start=self._aware_datetime(2026, 4, 11, 18, 0),
            placed_end=self._aware_datetime(2026, 4, 11, 19, 30),
        )

        breakdown = statistics_service.get_category_breakdown(self.user, None, None)

        self.assertEqual(len(breakdown), 2)
        self.assertEqual(breakdown[0]["name"], "Cognitive Improvement")
        self.assertEqual(breakdown[0]["hours"], 2.0)
        self.assertEqual(breakdown[0]["completion_pct"], 50)
        self.assertEqual(breakdown[1]["name"], "Fitness")
        self.assertEqual(breakdown[1]["hours"], 1.5)
        self.assertEqual(breakdown[1]["completion_pct"], 0)

    def test_filters_category_breakdown_to_selected_period(self):
        self._create_schedule_event(
            event=self.study_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 4, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 10, 10, 0),
        )
        self._create_schedule_event(
            event=self.gym_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 3, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 3, 10, 10, 0),
        )

        breakdown = statistics_service.get_category_breakdown(
            self.user,
            date(2026, 4, 1),
            date(2026, 4, 30),
        )

        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]["name"], "Cognitive Improvement")

    def test_ignores_schedule_events_from_other_users(self):
        self._create_schedule_event(
            event=self.study_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 4, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 10, 10, 0),
        )
        ScheduleEvent.objects.create(
            schedule=self.other_schedule,
            event=self.other_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.other_user,
            occurrence_index=1,
            placed_start=self._aware_datetime(2026, 4, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 10, 12, 0),
        )

        breakdown = statistics_service.get_category_breakdown(self.user, None, None)

        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]["name"], "Cognitive Improvement")

    def _create_schedule_event(self, event, status, placed_start, placed_end):
        occurrence_index = ScheduleEvent.objects.count() + 1
        return ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=event,
            status=status,
            placed_by=self.user,
            occurrence_index=occurrence_index,
            placed_start=placed_start,
            placed_end=placed_end,
        )

    def _aware_datetime(self, year, month, day, hour, minute):
        naive_datetime = datetime(year, month, day, hour, minute)
        return timezone.make_aware(naive_datetime)

class WeeklyHeatmapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls._create_user("heatmap-user")
        cls.other_user = cls._create_user("outside-heatmap-user")
        cls.category = Category.objects.create(
            name="weekly-heatmap-category",
            colour="#336699",
        )
        cls.other_category = Category.objects.create(
            name="weekly-heatmap-other-category",
            colour="#aa3344",
        )
        cls.schedule = Schedule.objects.create(title="Heatmap Schedule")
        cls.other_schedule = Schedule.objects.create(title="Other Heatmap Schedule")
        cls.event = cls._create_event("Heatmap Focus", cls.user, cls.category)
        cls.other_event = cls._create_event(
            "Other Heatmap Event",
            cls.other_user,
            cls.other_category,
        )

    @classmethod
    def _create_user(cls, username):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
        )

    @classmethod
    def _create_event(cls, title, user, category):
        return Event.objects.create(
            title=title,
            category=category,
            user=user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )

    def test_returns_empty_list_when_user_has_no_completed_events(self):
        heatmap = statistics_service.get_weekly_heatmap(self.user, None, None)

        self.assertEqual(heatmap, [])

    def test_groups_completed_events_into_week_rows(self):
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 13, 10, 0),
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 15, 12, 0),
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 15, 18, 0),
        )

        heatmap = statistics_service.get_weekly_heatmap(self.user, None, None)

        self.assertEqual(len(heatmap), 1)
        self.assertEqual(heatmap[0]["week_start"], date(2026, 4, 13))
        self.assertEqual(heatmap[0]["days"], [1, 0, 2, 0, 0, 0, 0])
        self.assertEqual(heatmap[0]["max"], 2)

    def test_includes_zero_count_weeks_between_first_and_last_completion(self):
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 7, 10, 0),
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 22, 10, 0),
        )

        heatmap = statistics_service.get_weekly_heatmap(self.user, None, None)

        self.assertEqual(len(heatmap), 3)
        self.assertEqual(heatmap[0]["week_start"], date(2026, 4, 6))
        self.assertEqual(heatmap[1]["week_start"], date(2026, 4, 13))
        self.assertEqual(heatmap[2]["week_start"], date(2026, 4, 20))
        self.assertEqual(heatmap[1]["days"], [0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(heatmap[1]["max"], 1)

    def test_filters_heatmap_to_selected_period(self):
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 10, 10, 0),
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 3, 10, 10, 0),
        )

        heatmap = statistics_service.get_weekly_heatmap(
            self.user,
            date(2026, 4, 1),
            date(2026, 4, 30),
        )

        self.assertEqual(len(heatmap), 1)
        self.assertEqual(heatmap[0]["week_start"], date(2026, 4, 6))
        self.assertEqual(heatmap[0]["days"], [0, 0, 0, 0, 1, 0, 0])

    def test_ignores_non_completed_events(self):
        self._create_schedule_event(
            status=ScheduleEvent.Status.SCHEDULED,
            placed_end=self._aware_datetime(2026, 4, 10, 10, 0),
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.MISSED,
            placed_end=self._aware_datetime(2026, 4, 11, 10, 0),
        )

        heatmap = statistics_service.get_weekly_heatmap(self.user, None, None)

        self.assertEqual(heatmap, [])

    def test_ignores_completed_events_from_other_users(self):
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_end=self._aware_datetime(2026, 4, 10, 10, 0),
        )
        ScheduleEvent.objects.create(
            schedule=self.other_schedule,
            event=self.other_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.other_user,
            occurrence_index=1,
            placed_end=self._aware_datetime(2026, 4, 10, 12, 0),
        )

        heatmap = statistics_service.get_weekly_heatmap(self.user, None, None)

        self.assertEqual(len(heatmap), 1)
        self.assertEqual(heatmap[0]["days"], [0, 0, 0, 0, 1, 0, 0])

    def _create_schedule_event(self, status, placed_end):
        occurrence_index = ScheduleEvent.objects.count() + 1
        placed_start = placed_end - timezone.timedelta(hours=1)

        return ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=self.event,
            status=status,
            placed_by=self.user,
            occurrence_index=occurrence_index,
            placed_start=placed_start,
            placed_end=placed_end,
        )

    def _aware_datetime(self, year, month, day, hour, minute):
        naive_datetime = datetime(year, month, day, hour, minute)
        return timezone.make_aware(naive_datetime)

class StreakLeaderboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls._create_user("streak-user")
        cls.other_user = cls._create_user("other-streak-user")
        cls.category = Category.objects.create(
            name="streak-leaderboard-category",
            colour="#336699",
        )
        cls.other_category = Category.objects.create(
            name="streak-leaderboard-other-category",
            colour="#aa3344",
        )
        cls.schedule = Schedule.objects.create(title="Streak Schedule")
        cls.other_schedule = Schedule.objects.create(title="Other Streak Schedule")
        cls.study_event = cls._create_event("Study", cls.user, cls.category)
        cls.gym_event = cls._create_event("Gym", cls.user, cls.category)
        cls.reading_event = cls._create_event("Reading", cls.user, cls.category)
        cls.other_event = cls._create_event(
            "Other User Event",
            cls.other_user,
            cls.other_category,
        )

    @classmethod
    def _create_user(cls, username):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
        )

    @classmethod
    def _create_event(cls, title, user, category):
        return Event.objects.create(
            title=title,
            category=category,
            user=user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )

    def test_returns_zero_when_template_has_no_resolved_instances(self):
        streak = statistics_service.get_streak_for_template(self.study_event)

        self.assertEqual(streak, 0)

    def test_counts_consecutive_completed_instances_from_most_recent(self):
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.MISSED, 1, 1)
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 2, 2)
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 3, 3)

        streak = statistics_service.get_streak_for_template(self.study_event)

        self.assertEqual(streak, 2)

    def test_breaks_streak_on_most_recent_missed_instance(self):
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 1, 1)
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.MISSED, 2, 2)

        streak = statistics_service.get_streak_for_template(self.study_event)

        self.assertEqual(streak, 0)

    def test_returns_ranked_active_streaks_for_user_templates(self):
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 1, 1)
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 2, 2)
        self._create_resolved_instance(self.gym_event, ScheduleEvent.Status.COMPLETED, 3, 1)
        self._create_resolved_instance(self.reading_event, ScheduleEvent.Status.MISSED, 4, 1)

        leaderboard = statistics_service.get_streak_leaderboard(self.user)

        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0]["title"], self.study_event.title)
        self.assertEqual(leaderboard[0]["streak"], 2)
        self.assertEqual(leaderboard[1]["title"], self.gym_event.title)
        self.assertEqual(leaderboard[1]["streak"], 1)

    def test_excludes_templates_with_zero_active_streak(self):
        self._create_resolved_instance(self.reading_event, ScheduleEvent.Status.MISSED, 1, 1)

        leaderboard = statistics_service.get_streak_leaderboard(self.user)

        self.assertEqual(leaderboard, [])

    def test_ignores_templates_belonging_to_other_users(self):
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 1, 1)
        ScheduleEvent.objects.create(
            schedule=self.other_schedule,
            event=self.other_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.other_user,
            occurrence_index=1,
            placed_start=self._aware_datetime(2026, 3, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 3, 10, 10, 0),
        )

        leaderboard = statistics_service.get_streak_leaderboard(self.user)

        self.assertEqual(len(leaderboard), 1)
        self.assertEqual(leaderboard[0]["title"], self.study_event.title)

    def test_applies_limit_to_leaderboard_rows(self):
        self._create_resolved_instance(self.study_event, ScheduleEvent.Status.COMPLETED, 1, 1)
        self._create_resolved_instance(self.gym_event, ScheduleEvent.Status.COMPLETED, 2, 1)
        self._create_resolved_instance(self.reading_event, ScheduleEvent.Status.COMPLETED, 3, 1)

        leaderboard = statistics_service.get_streak_leaderboard(self.user, limit=2)

        self.assertEqual(len(leaderboard), 2)

    def _create_resolved_instance(self, event, status, day, occurrence_index):
        return ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=event,
            status=status,
            placed_by=self.user,
            occurrence_index=occurrence_index,
            placed_start=self._aware_datetime(2026, 3, day, 9, 0),
            placed_end=self._aware_datetime(2026, 3, day, 10, 0),
        )

    def _aware_datetime(self, year, month, day, hour, minute):
        naive_datetime = datetime(year, month, day, hour, minute)
        return timezone.make_aware(naive_datetime)
    
class WeeklyTrendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls._create_user("trend-user")
        cls.other_user = cls._create_user("other-trend-user")
        cls.category = Category.objects.create(
            name="weekly-trends-category",
            colour="#336699",
        )
        cls.other_category = Category.objects.create(
            name="weekly-trends-other-category",
            colour="#aa3344",
        )
        cls.schedule = Schedule.objects.create(title="Trend Schedule")
        cls.other_schedule = Schedule.objects.create(title="Other Trend Schedule")
        cls.event = cls._create_event("Trend Event", cls.user, cls.category)
        cls.other_event = cls._create_event(
            "Other Trend Event",
            cls.other_user,
            cls.other_category,
        )

    @classmethod
    def _create_user(cls, username):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
        )

    @classmethod
    def _create_event(cls, title, user, category):
        return Event.objects.create(
            title=title,
            category=category,
            user=user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_twelve_weeks_ordered_oldest_to_newest(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 15)

        trends = statistics_service.get_weekly_trends(self.user)

        self.assertEqual(len(trends), 12)
        self.assertEqual(trends[0]["label"], "26 Jan")
        self.assertEqual(trends[-1]["label"], "13 Apr")

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_calculates_weekly_completion_percentage_and_hours(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 15)
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 4, 14, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 14, 10, 30),
            occurrence_index=1,
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.COMPLETED,
            placed_start=self._aware_datetime(2026, 4, 15, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 15, 10, 0),
            occurrence_index=2,
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.MISSED,
            placed_start=self._aware_datetime(2026, 4, 16, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 16, 10, 0),
            occurrence_index=3,
        )
        self._create_schedule_event(
            status=ScheduleEvent.Status.SCHEDULED,
            placed_start=self._aware_datetime(2026, 4, 17, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 17, 11, 0),
            occurrence_index=4,
        )

        trends = statistics_service.get_weekly_trends(self.user)
        latest_week = trends[-1]

        self.assertEqual(latest_week["label"], "13 Apr")
        self.assertEqual(latest_week["completion_pct"], 67)
        self.assertEqual(latest_week["hours"], 4.5)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_returns_zero_values_for_empty_weeks(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 15)

        trends = statistics_service.get_weekly_trends(self.user)

        self.assertEqual(trends[-1]["completion_pct"], 0)
        self.assertEqual(trends[-1]["hours"], 0.0)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_ignores_events_from_other_users(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 15)
        ScheduleEvent.objects.create(
            schedule=self.other_schedule,
            event=self.other_event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.other_user,
            occurrence_index=1,
            placed_start=self._aware_datetime(2026, 4, 14, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 14, 10, 0),
        )

        trends = statistics_service.get_weekly_trends(self.user)

        self.assertEqual(trends[-1]["completion_pct"], 0)
        self.assertEqual(trends[-1]["hours"], 0.0)

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_respects_custom_week_count(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 15)

        trends = statistics_service.get_weekly_trends(self.user, num_weeks=4)

        self.assertEqual(len(trends), 4)
        self.assertEqual(trends[0]["label"], "23 Mar")
        self.assertEqual(trends[-1]["label"], "13 Apr")

    def _create_schedule_event(
        self,
        status,
        placed_start,
        placed_end,
        occurrence_index,
    ):
        return ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=self.event,
            status=status,
            placed_by=self.user,
            occurrence_index=occurrence_index,
            placed_start=placed_start,
            placed_end=placed_end,
        )

    def _aware_datetime(self, year, month, day, hour, minute):
        naive_datetime = datetime(year, month, day, hour, minute)
        return timezone.make_aware(naive_datetime)