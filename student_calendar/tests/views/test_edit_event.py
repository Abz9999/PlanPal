from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from student_calendar.models import Category, Event
from student_calendar.models.schedule import Schedule
from student_calendar.models.schedule_event import ScheduleEvent
from student_calendar.models.user_schedule import UserSchedule


class EditEventViewTestCase(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
            email="test@test.com",
            first_name="Test",
            last_name="User",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="password123",
            email="other@test.com",
            first_name="Other",
            last_name="User",
        )

        self.category = Category.objects.create(
            name="Study",
            colour="#3788d8",
        )

        self.schedule = Schedule.objects.create(
            title="testuser's Schedule",
            is_active=True,
        )
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

        self.event = Event.objects.create(
            title="Original Event",
            category=self.category,
            user=self.user,
            duration=60,
            repeat_days=1,
            repeat_weeks=2,
            number_of_days=1,
            importance=Event.Priority.LOW,
            max_instances=2,
        )

        ScheduleEvent.objects.create(
            event=self.event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.CREATED,
            occurrence_index=1,
            placed_by=self.user,
        )
        ScheduleEvent.objects.create(
            event=self.event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.CREATED,
            occurrence_index=2,
            placed_by=self.user,
        )

        self.other_event = Event.objects.create(
            title="Other User Event",
            category=self.category,
            user=self.other_user,
            duration=30,
            repeat_days=1,
            repeat_weeks=1,
            number_of_days=1,
            importance=Event.Priority.LOW,
            max_instances=1,
        )

        self.post_data = {
            "title": "Updated Event",
            "category": self.category.pk,
            "repeat_days": ["1"],
            "repeat_weeks": 1,
            "number_of_days": 1,
            "importance": 1,
            "hours": 1,
            "minutes": 30,
        }

    # url and login tests
    def test_edit_event_url(self):
        url = reverse("edit_event", args=[self.event.id])
        self.assertEqual(url, f"/event/{self.event.id}/edit/")

    def test_edit_event_redirects_if_not_logged_in(self):
        url = reverse("edit_event", args=[self.event.id])
        response = self.client.get(url)
        self.assertRedirects(response, f"/?next={url}")

    def test_post_redirects_if_not_logged_in(self):
        url = reverse("edit_event", args=[self.event.id])
        response = self.client.post(url, self.post_data)
        self.assertRedirects(response, f"/?next={url}")

    # GET tests
    def test_get_edit_event_renders_form(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("edit_event", args=[self.event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/edit_event_form.html")

    def test_get_edit_event_has_correct_event_in_context(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("edit_event", args=[self.event.id]))

        self.assertEqual(response.context["event"], self.event)

    def test_get_returns_404_for_other_users_event(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("edit_event", args=[self.other_event.id]))

        self.assertEqual(response.status_code, 404)

    # POST success tests
    def test_valid_post_returns_ok_true(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.post(reverse("edit_event", args=[self.event.id]), self.post_data)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})

    def test_valid_post_updates_title(self):
        self.client.login(username="testuser", password="password123")
        data = self.post_data.copy()
        data["title"] = "Renamed Event"
        self.client.post(reverse("edit_event", args=[self.event.id]), data)

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Renamed Event")

    def test_valid_post_recalculates_max_instances(self):
        self.client.login(username="testuser", password="password123")
        data = self.post_data.copy()
        data["repeat_weeks"] = 3
        self.client.post(reverse("edit_event", args=[self.event.id]), data)

        self.event.refresh_from_db()
        self.assertEqual(self.event.max_instances, 3)

    def test_valid_post_deletes_old_schedule_events(self):
        self.client.login(username="testuser", password="password123")
        self.client.post(reverse("edit_event", args=[self.event.id]), self.post_data)

        remaining = ScheduleEvent.objects.filter(event=self.event)
        self.assertEqual(remaining.count(), 1)

    def test_valid_post_creates_correct_number_of_instances(self):
        self.client.login(username="testuser", password="password123")
        data = self.post_data.copy()
        data["repeat_days"] = ["1", "2"]
        data["number_of_days"] = 2
        data["repeat_weeks"] = 2
        self.client.post(reverse("edit_event", args=[self.event.id]), data)

        instances = ScheduleEvent.objects.filter(event=self.event)
        self.assertEqual(instances.count(), 4)

    def test_new_instances_all_have_created_status(self):
        self.client.login(username="testuser", password="password123")
        self.client.post(reverse("edit_event", args=[self.event.id]), self.post_data)

        instances = ScheduleEvent.objects.filter(event=self.event)
        for instance in instances:
            self.assertEqual(instance.status, ScheduleEvent.Status.CREATED)

    # POST failure tests
    def test_post_with_empty_title_returns_400(self):
        self.client.login(username="testuser", password="password123")
        data = self.post_data.copy()
        data["title"] = ""
        response = self.client.post(reverse("edit_event", args=[self.event.id]), data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertIn("errors", response.json())

    def test_invalid_post_does_not_change_event(self):
        self.client.login(username="testuser", password="password123")
        data = self.post_data.copy()
        data["title"] = ""
        self.client.post(reverse("edit_event", args=[self.event.id]), data)

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Original Event")

