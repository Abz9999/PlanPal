# Khan - tests for completed_events view

from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from student_calendar.models import (
    User, Event, Category, Schedule, ScheduleEvent, UserSchedule
)


class CompletedEventsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="pass123"
        )
        self.client.login(username="testuser", password="pass123")

        self.category = Category.objects.create(name="Study", colour="#0000FF")
        self.schedule = Schedule.objects.create(title="My Schedule", is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

        self.url = reverse('completed_events')

        # event with 1 completed and 1 created instance
        self.event_with_completed = Event.objects.create(
            title="Gym", user=self.user, category=self.category,
            duration=60, importance=3,
            number_of_days=1, repeat_days=1, max_instances=2,
        )
        ScheduleEvent.objects.create(
            event=self.event_with_completed, schedule=self.schedule,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=1, placed_by=self.user,
        )
        ScheduleEvent.objects.create(
            event=self.event_with_completed, schedule=self.schedule,
            status=ScheduleEvent.Status.CREATED,
            occurrence_index=2, placed_by=self.user,
        )

        # event with no completed instances
        self.event_no_completed = Event.objects.create(
            title="Study", user=self.user, category=self.category,
            duration=90, importance=4,
            number_of_days=1, repeat_days=1, max_instances=1,
        )
        ScheduleEvent.objects.create(
            event=self.event_no_completed, schedule=self.schedule,
            status=ScheduleEvent.Status.CREATED,
            occurrence_index=1, placed_by=self.user,
        )

    def test_only_events_with_completed_instances_appear(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        event_data = response.context['event_data']
        titles = [d['event'].title for d in event_data]
        self.assertIn('Gym', titles)
        self.assertNotIn('Study', titles)

    def test_completed_count_is_correct(self):
        response = self.client.get(self.url)
        event_data = response.context['event_data']
        gym = next(d for d in event_data if d['event'].title == 'Gym')
        self.assertEqual(gym['completed_count'], 1)

    def test_total_count_is_correct(self):
        response = self.client.get(self.url)
        event_data = response.context['event_data']
        gym = next(d for d in event_data if d['event'].title == 'Gym')
        self.assertEqual(gym['total_count'], 2)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_only_shows_current_users_events(self):
        # create another user with a completed event
        other_user = User.objects.create_user(
            username="other", email="other@test.com", password="pass123"
        )
        other_schedule = Schedule.objects.create(title="Other Schedule")
        UserSchedule.objects.create(user=other_user, schedule=other_schedule)
        other_event = Event.objects.create(
            title="Other Gym", user=other_user, category=self.category,
            duration=60, importance=3, number_of_days=1, repeat_days=1,
        )
        ScheduleEvent.objects.create(
            event=other_event, schedule=other_schedule,
            status=ScheduleEvent.Status.COMPLETED,
            occurrence_index=1, placed_by=other_user,
        )

        response = self.client.get(self.url)
        event_data = response.context['event_data']
        titles = [d['event'].title for d in event_data]
        self.assertNotIn('Other Gym', titles)

    def test_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'completed_events.html')

    def test_no_completed_events_returns_empty(self):
        # delete the completed instance
        ScheduleEvent.objects.filter(
            status=ScheduleEvent.Status.COMPLETED
        ).delete()
        response = self.client.get(self.url)
        event_data = response.context['event_data']
        self.assertEqual(len(event_data), 0)

    def test_modal_id_set_correctly(self):
        response = self.client.get(self.url)
        event_data = response.context['event_data']
        gym = next(d for d in event_data if d['event'].title == 'Gym')
        self.assertEqual(gym['modal_id'], f'modal-{self.event_with_completed.id}')


# Tests added by teammate — kept for additional coverage

class CompletedEventsViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('completed_events')
        self.user = User.objects.create_user(
            username='testuser2',
            first_name='Test',
            last_name='User',
            email='testuser2@example.com',
            password='Password123!'
        )
        self.category = Category.objects.get(name='Other')
        self.now = timezone.now()
        self.event = Event.objects.create(
            title='Completed Event',
            start=self.now,
            end=self.now + timedelta(hours=1),
            duration=60,
            category=self.category,
            importance=Event.Priority.MEDIUM,
            user=self.user
        )
        self.schedule = Schedule.objects.create(title='Test Schedule')
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)
        self.schedule_event = ScheduleEvent.objects.create(
            event=self.event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.user
        )

    def log_in(self):
        self.client.login(username='testuser2', password='Password123!')

    def test_url(self):
        self.assertEqual(self.url, '/completed/')

    def test_redirects_when_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_returns_200(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_correct_template_used(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'completed_events.html')

    def test_completed_event_appears_in_response(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertContains(response, 'Completed Event')

    def test_event_with_no_completed_instances_does_not_appear(self):
        pending_event = Event.objects.create(
            title='Pending Event',
            start=self.now,
            end=self.now + timedelta(hours=1),
            duration=60,
            category=self.category,
            importance=Event.Priority.MEDIUM,
            user=self.user
        )
        ScheduleEvent.objects.create(
            event=pending_event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.CREATED,
            placed_by=self.user
        )
        self.log_in()
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Pending Event')

    def test_other_users_completed_events_do_not_appear(self):
        other_user = User.objects.create_user(
            username='otheruser3',
            first_name='Other',
            last_name='User',
            email='other3@example.com',
            password='Password123!'
        )
        other_event = Event.objects.create(
            title="Other User's Event",
            start=self.now,
            end=self.now + timedelta(hours=1),
            duration=60,
            category=self.category,
            importance=Event.Priority.MEDIUM,
            user=other_user
        )
        ScheduleEvent.objects.create(
            event=other_event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=other_user
        )
        self.log_in()
        response = self.client.get(self.url)
        self.assertNotContains(response, "Other User's Event")

    def test_context_contains_event_data(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertIn('event_data', response.context)

    def test_completed_count_multiple_instances(self):
        ScheduleEvent.objects.create(
            event=self.event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.COMPLETED,
            placed_by=self.user
        )
        self.log_in()
        response = self.client.get(self.url)
        entry = next(d for d in response.context['event_data'] if d['event'] == self.event)
        self.assertEqual(entry['completed_count'], 2)

    def test_total_count_includes_non_completed_instances(self):
        ScheduleEvent.objects.create(
            event=self.event,
            schedule=self.schedule,
            status=ScheduleEvent.Status.SCHEDULED,
            placed_by=self.user
        )
        self.log_in()
        response = self.client.get(self.url)
        entry = next(d for d in response.context['event_data'] if d['event'] == self.event)
        self.assertEqual(entry['completed_count'], 1)
        self.assertEqual(entry['total_count'], 2)
