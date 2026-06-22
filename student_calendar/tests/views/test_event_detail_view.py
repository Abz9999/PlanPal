from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from student_calendar.models import Category, Event


def reverse_next(name, next_url):
    return f"{reverse(name)}?next={next_url}"


class EventDetailViewTestCase(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
            email="test@test.com",
            first_name="Test",
            last_name="User",
        )

        self.category = Category.objects.create(
            name="Study",
            colour="#3788d8",
        )

        self.fixed_event = Event.objects.create(
            title="Fixed Event",
            category=self.category,
            user=self.user,
            start=timezone.make_aware(datetime(2026, 3, 22, 10, 0)),
            end=timezone.make_aware(datetime(2026, 3, 22, 11, 30)),
            repeat_days=1,
            repeat_weeks=1,
            description="Bring notes and laptop.",
            importance=Event.Priority.HIGH,
        )

        self.time_only_event = Event.objects.create(
            title="Morning Routine",
            category=self.category,
            user=self.user,
            start=timezone.make_aware(datetime(1970, 1, 1, 8, 0)),
            end=timezone.make_aware(datetime(1970, 1, 1, 8, 45)),
            repeat_days=1,
            repeat_weeks=1,
            description="Start the day properly.",
            importance=Event.Priority.MEDIUM,
        )

        self.flexible_event = Event.objects.create(
            title="Read Notes",
            category=self.category,
            user=self.user,
            duration=90,
            repeat_days=1,
            repeat_weeks=1,
            description="Catch up on revision notes.",
            importance=Event.Priority.LOW,
        )

    def test_url(self):
        url = reverse("event_detail", args=[self.fixed_event.id])
        self.assertEqual(url, f"/event/{self.fixed_event.id}")

    def test_get_requires_login(self):
        url = reverse("event_detail", args=[self.fixed_event.id])
        response = self.client.get(url, follow=True)

        self.assertRedirects(
            response,
            reverse_next("home", url),
            status_code=302,
            target_status_code=200,
        )
        self.assertTemplateUsed(response, "homepage.html")

    def test_get_event_detail(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.fixed_event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "event_detail.html")
        self.assertEqual(response.context["event"], self.fixed_event)
        self.assertContains(response, "Fixed Event")
        self.assertContains(response, "Bring notes and laptop.")
        self.assertContains(response, "High")

    def test_fixed_event_does_not_show_duration_label(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.fixed_event.id]))

        self.assertNotContains(response, "Duration:")

    def test_time_only_event_shows_time_range(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.time_only_event.id]))

        self.assertContains(response, "08:00")
        self.assertContains(response, "08:45")
        self.assertNotContains(response, "Duration:")

    def test_flexible_event_shows_formatted_duration(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.flexible_event.id]))

        self.assertContains(response, "Duration:")
        self.assertContains(response, "1 hr 30 mins")

    def test_delete_modal_markup_is_present(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.fixed_event.id]))

        self.assertContains(response, 'data-bs-toggle="modal"')
        self.assertContains(response, 'data-bs-target="#deleteModal"')
        self.assertContains(response, 'id="deleteModal"')
        self.assertContains(
            response,
            f'action="{reverse("delete_event", args=[self.fixed_event.id])}"',
        )
        self.assertContains(response, 'Are you sure you want to delete "Fixed Event"?')
