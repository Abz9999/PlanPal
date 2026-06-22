#Created by Ashrith
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from student_calendar.models import Event, Schedule, ScheduleEvent, Category



User = get_user_model()

class ClearScheduleTest(TestCase):

    def setUp(self):
        # ---- User creation ----
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

        # ---- Create a Schedule for this User ----
        # is_active=True because clear_schedule filters on the active schedule.
        self.schedule = Schedule.objects.create(title="Test Schedule", is_active=True)
        from student_calendar.models import UserSchedule
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)


        # ---- create some events ----
        self.category = Category.objects.create(name="Test", colour="#FF0000")
        self.event1 = Event.objects.create(title="Task 1", start="2026-05-26 10:00", end="2026-05-26 11:00", category=self.category, user=self.user, number_of_days=1, repeat_days=1)
        self.event2 = Event.objects.create(title="Task 2", start="2026-05-26 12:00", end="2026-05-26 13:00", category=self.category, user=self.user, number_of_days=1, repeat_days=1)

        # ---- Schedule Events ----
        ScheduleEvent.objects.create(schedule=self.schedule, event=self.event1, status=ScheduleEvent.Status.SCHEDULED, placed_by=self.user)
        ScheduleEvent.objects.create(schedule=self.schedule, event=self.event2, status=ScheduleEvent.Status.SCHEDULED, placed_by=self.user)

        # Unscheduled Event
        ScheduleEvent.objects.create(schedule=self.schedule, event=self.event1, status=ScheduleEvent.Status.CREATED, placed_by=self.user)

    def test_clear_schedule(self):
        #  Call clear_schedule view 
        response = self.client.post(reverse("clear_schedule"))  # ensure URL name matches urls.py
        self.assertEqual(response.status_code, 302)  # should redirect to main page

        # ---- If the event is scheduled, it should be cleared. ----
        schedule_events = ScheduleEvent.objects.filter(status=ScheduleEvent.Status.SCHEDULED)
        self.assertEqual(schedule_events.count(), 0)

        # ---- If the event isn't scheduled(but created), it should remain ----
        created_events = ScheduleEvent.objects.filter(status=ScheduleEvent.Status.CREATED)
        self.assertEqual(created_events.count(), 3)

        # ---- Check that Event objects themselves still exist ----
        self.assertEqual(Event.objects.count(), 2)