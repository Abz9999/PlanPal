from datetime import date
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from student_calendar.models import ScheduleEvent, Category, Event, Schedule
import json

class StatisticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="statsuser",
            email="stats@example.com",
            password="testpassword123",
        )
        self.url = reverse("statistics")

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)
        expected_url = f"{reverse(settings.LOGIN_URL)}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
    )

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_sets_week_period_context_for_logged_in_user(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 1)
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url, {"period": "week"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["period"], "week")
        self.assertEqual(response.context["start_date"], date(2026, 3, 30))
        self.assertEqual(response.context["end_date"], date(2026, 4, 5))

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_sets_month_period_context_for_logged_in_user(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 2)
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url, {"period": "month"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["period"], "month")
        self.assertEqual(response.context["start_date"], date(2026, 4, 1))
        self.assertEqual(response.context["end_date"], date(2026, 4, 30))

    def test_defaults_invalid_period_to_all(self):
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url, {"period": "not-real"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["period"], "all")
        self.assertIsNone(response.context["start_date"])
        self.assertIsNone(response.context["end_date"])

    def test_defaults_missing_period_to_all(self):
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["period"], "all")
        self.assertIsNone(response.context["start_date"])
        self.assertIsNone(response.context["end_date"])

    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_adds_hero_stats_to_context(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 14)
        schedule = Schedule.objects.create(title="Main Schedule")
        category = Category.objects.create(name="Study", colour="#336699")
        event = Event.objects.create(
            title="Focus",
            category=category,
            user=self.user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )
        ScheduleEvent.objects.create(
            schedule=schedule,
            event=event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.user,
            occurrence_index=1,
        )
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["hero"]["total_completed"], 1)
    
    def test_adds_category_breakdown_to_context_and_json(self):
        schedule = Schedule.objects.create(title="Main Schedule")
        category = Category.objects.create(name="Study", colour="#336699")
        event = Event.objects.create(
            title="Focus",
            category=category,
            user=self.user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )
        ScheduleEvent.objects.create(
            schedule=schedule,
            event=event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.user,
            occurrence_index=1,
            placed_start=self._aware_datetime(2026, 4, 10, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 10, 11, 0),
        )
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["categories"][0]["name"], "Study")

        categories_json = json.loads(response.context["categories_json"])
        self.assertEqual(categories_json[0]["name"], "Study")
        self.assertEqual(categories_json[0]["colour"], "#336699")
        self.assertEqual(categories_json[0]["hours"], 2.0)

    def _aware_datetime(self, year, month, day, hour, minute):
        from datetime import datetime

        from django.utils import timezone

        naive_datetime = datetime(year, month, day, hour, minute)
        return timezone.make_aware(naive_datetime)
    
    def test_adds_heatmap_to_context(self):
        schedule = Schedule.objects.create(title="Heatmap View Schedule")
        category = Category.objects.create(
            name="heatmap-view-category-fixed",
            colour="#336699",
        )
        event = Event.objects.create(
            title="Heatmap View Event",
            category=category,
            user=self.user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )
        ScheduleEvent.objects.create(
            schedule=schedule,
            event=event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.user,
            occurrence_index=1,
            placed_start=self._aware_datetime(2026, 2, 18, 9, 0),
            placed_end=self._aware_datetime(2026, 2, 18, 10, 0),
        )
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url, {"period": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["heatmap"]), 1)
        self.assertEqual(response.context["heatmap"][0]["week_start"], date(2026, 2, 16))
        self.assertEqual(response.context["heatmap"][0]["days"], [0, 0, 1, 0, 0, 0, 0])

    
    def test_adds_streak_leaderboard_to_context(self):
            schedule = Schedule.objects.create(title="Streak View Schedule")
            category = Category.objects.create(
                name="streak-view-category-fixed",
                colour="#336699",
            )
            event = Event.objects.create(
                title="Streak View Event",
                category=category,
                user=self.user,
                duration=60,
                repeat_weeks=1,
                repeat_days=Event.MON,
                number_of_days=5,
                importance=Event.Priority.MEDIUM,
                max_instances=5,
            )
            ScheduleEvent.objects.create(
                schedule=schedule,
                event=event,
                status=ScheduleEvent.Status.COMPLETED,
                placed_by=self.user,
                occurrence_index=1,
                placed_start=self._aware_datetime(2026, 3, 2, 9, 0),
                placed_end=self._aware_datetime(2026, 3, 2, 10, 0),
            )
            self.client.login(username="statsuser", password="testpassword123")

            response = self.client.get(self.url, {"period": "all"})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["streaks"]), 1)
            self.assertEqual(response.context["streaks"][0]["title"], event.title)
            self.assertEqual(response.context["streaks"][0]["streak"], 1)

    
    @patch("student_calendar.statistics_service.timezone.localdate")
    def test_adds_trends_to_context_and_json(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 4, 15)
        schedule = Schedule.objects.create(title="Trend View Schedule")
        category = Category.objects.create(
            name="trend-view-category",
            colour="#336699",
        )
        event = Event.objects.create(
            title="Trend View Event",
            category=category,
            user=self.user,
            duration=60,
            repeat_weeks=1,
            repeat_days=Event.MON,
            number_of_days=1,
            importance=Event.Priority.MEDIUM,
            max_instances=1,
        )
        ScheduleEvent.objects.create(
            schedule=schedule,
            event=event,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.user,
            occurrence_index=1,
            placed_start=self._aware_datetime(2026, 4, 14, 9, 0),
            placed_end=self._aware_datetime(2026, 4, 14, 10, 0),
        )
        self.client.login(username="statsuser", password="testpassword123")

        response = self.client.get(self.url, {"period": "week"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["trends"]), 12)
        self.assertEqual(response.context["trends"][-1]["label"], "13 Apr")
        self.assertEqual(response.context["trends"][-1]["completion_pct"], 100)
        self.assertEqual(response.context["trends"][-1]["hours"], 1.0)
        
        trends_json = json.loads(response.context["trends_json"])
        self.assertEqual(trends_json[-1]["label"], "13 Apr")
        self.assertEqual(trends_json[-1]["completion_pct"], 100)
        self.assertEqual(trends_json[-1]["hours"], 1.0)
    
    

    
    