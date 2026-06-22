from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from student_calendar.models import Event, Category


class DeleteEventTests(TestCase):

    def setUp(self):
        User = get_user_model()

        # create user
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
            email="test@test.com",
            first_name="Test",
            last_name="User"
        )

        # login client
        self.client.login(username="testuser", password="password123")

        # create category
        self.category = Category.objects.create(name="Study")

        # create event
        self.event = Event.objects.create(
            title="Test Event",
            category=self.category,
            user=self.user,
            repeat_days=0,
            repeat_weeks=0
        )

    def test_delete_event_post(self):
        # Event should be deleted with POST request

        response = self.client.post(
            reverse("delete_event", args=[self.event.id])
        )

        self.assertFalse(Event.objects.filter(id=self.event.id).exists())


    def test_delete_event_requires_post(self):
        # GET request should NOT delete event

        response = self.client.get(
            reverse("delete_event", args=[self.event.id])
        )

        self.assertTrue(Event.objects.filter(id=self.event.id).exists())


    def test_user_cannot_delete_other_users_event(self):
        # User should not delete someone else's event

        User = get_user_model()

        other_user = User.objects.create_user(
            username="other",
            password="password123",
            email="other@test.com",
            first_name="Other",
            last_name="User"
        )

        other_event = Event.objects.create(
            title="Other Event",
            category=self.category,
            user=other_user,
            repeat_days=0,
            repeat_weeks=0
        )

        response = self.client.post(
            reverse("delete_event", args=[other_event.id])
        )

        self.assertTrue(Event.objects.filter(id=other_event.id).exists())