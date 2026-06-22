# Created by Theodore Tsiberopoulos

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from student_calendar.models import User, Event, Schedule, ScheduleEvent, UserSchedule, Category
from student_calendar.tests.test_utility import reverse_next
from datetime import datetime, timedelta


class DashboardViewTestCase(TestCase):
    """Tests of the dashboard view"""

    fixtures = ['student_calendar/tests/fixtures/default_user.json',
                'student_calendar/tests/fixtures/other_users.json']

    def setUp(self):
        self.url = reverse('dashboard')
        self.user = User.objects.get(username='exampleuser')
        self.today = datetime.now()
        self.event = Event.objects.create(
            title='Test Event',
            start=timezone.make_aware(self.today+timedelta(hours=2)),
            end=timezone.make_aware(self.today+timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        self.schedule = Schedule.objects.create(title='Test Schedule')
        self.schedule_event = ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=self.event,
            placed_start=self.event.start,
            placed_end=self.event.end,
            status=ScheduleEvent.Status.SCHEDULED
        )
        self.user_schedule = UserSchedule.objects.create(
            user=self.user,
            schedule=self.schedule
        )

    def test_url(self):
        self.assertEqual(self.url, '/dashboard/')

    def test_redirects_when_not_logged_in(self):
        response = self.client.get(self.url)
        redirect = reverse_next('home', self.url)
        self.assertRedirects(response, redirect, status_code=302, target_status_code=200)

    def test_get_dashboard(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertContains(response, 'Test Event')

    def test_other_users_events_do_not_appear(self):
        self.log_in()

        # create an event assigned to someone else
        other_user = User.objects.get(username='exampleuser2')
        other_user_event = Event.objects.create(
            title='Someone else\'s event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=other_user
        )
        other_user_event.save()

        # the other user's event should not appear in response
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Someone else\'s event')
        self.assertContains(response, 'Test Event')

    def test_no_events_message(self):
        self.client.login(username='exampleuser2', password='Password123')
        response = self.client.get(self.url)
        self.assertContains(response, 'You don\'t have any events...')

    def test_name_sorting(self):
        self.log_in()
        event_beginning_in_a = Event.objects.create(
            title='AAAAA',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        event_beginning_in_a.save()
        event_beginning_in_z = Event.objects.create(
            title='ZZZZZ',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        event_beginning_in_z.save()

        # title (a-z) sort should be in order: AAAAA, Test Event, ZZZZZ
        self._test_event_card_sequence_and_return_response('?sort=title',
                                                           [
                                                               'AAAAA',
                                                               'Test Event',
                                                               'ZZZZZ'])

        # title (z-a) sort should be in order: ZZZZZ, Test Event, AAAAA
        self._test_event_card_sequence_and_return_response('?sort=-title',
                                                           [
                                                               'ZZZZZ',
                                                               'Test Event',
                                                               'AAAAA'])

        # without sort parameters, view should default to (title a-z)
        self._test_event_card_sequence_and_return_response('',
                                                           [
                                                               'AAAAA',
                                                               'Test Event',
                                                               'ZZZZZ'])

        # with an invalid sort parameter, view should return (title a-z)
        self._test_event_card_sequence_and_return_response('?sort=bad_data',
                                                           [
                                                               'AAAAA',
                                                               'Test Event',
                                                               'ZZZZZ'])

    def test_importance_sorting(self):
        self.log_in()
        more_important_event = Event.objects.create(
            title='More Important Event',
            start=timezone.make_aware(self.today+timedelta(hours=2)),
            end=timezone.make_aware(self.today+timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.CRITICAL,
            duration=120,
            user=self.user
        )
        more_important_event.save()
        less_important_event = Event.objects.create(
            title='Less Important Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.VERY_LOW,
            duration=120,
            user=self.user
        )
        less_important_event.save()

        # importance (high-low) should be in order: More Important Event, Test Event, Less Important Event
        self._test_event_card_sequence_and_return_response('?sort=importance',
                                                           [
                                                               'More Important Event',
                                                               'Test Event',
                                                               'Less Important Event'])

        # importance (low-high) should be in order: Less Important Event, Test Event, More Important Event
        self._test_event_card_sequence_and_return_response('?sort=-importance',
                                                           [
                                                               'Less Important Event',
                                                               'Test Event',
                                                               'More Important Event'])

        # sort parameters should be case-insensitive
        # putting this test here so that it can't be due to the bad data autocorrect
        self._test_event_card_sequence_and_return_response('?sort=ImPoRtAnCe',
                                                           [
                                                               'More Important Event',
                                                               'Test Event',
                                                               'Less Important Event'])

    def test_amount_placed_sorting(self):
        self.log_in()
        self.create_advanced_sorting_fixtures()

        # create an event that appears in a schedule multiple times
        multi_scheduled_event = Event.objects.create(
            title='Multiple Scheduled Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        multi_scheduled_event.save()
        for i in range(2):
            new_schedule_event = ScheduleEvent.objects.create(
                schedule=self.schedule,
                event=multi_scheduled_event,
                placed_start=multi_scheduled_event.start,
                placed_end=multi_scheduled_event.end,
                status=ScheduleEvent.Status.SCHEDULED
            )
            new_schedule_event.save()

        # sorting by amount placed (most-least)
        # this response should have the multiple scheduled event appear before the test event
        response = self._test_event_card_sequence_and_return_response('?sort=amount_placed',
                                                                      [
                                                                          'Multiple Scheduled Event',
                                                                          'Test Event'])
        self._test_advanced_sorting_fixtures(response=response)

        # sorting by amount placed (least-most) should put the test event before the multiple scheduled event
        self._test_event_card_sequence_and_return_response('?sort=-amount_placed',
                                                           [
                                                               'Test Event',
                                                               'Multiple Scheduled Event'])

    def test_next_scheduled_sorting(self):
        self.log_in()
        self.create_advanced_sorting_fixtures()

        # create an event that was scheduled before today
        expired_event = Event.objects.create(
            title='Expired Event',
            start=timezone.make_aware(self.today - timedelta(days=2)),
            end=timezone.make_aware(self.today - timedelta(days=2)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        expired_event.save()
        expired_schedule_event = ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=expired_event,
            placed_start=expired_event.start,
            placed_end=expired_event.end,
            status=ScheduleEvent.Status.SCHEDULED
        )
        expired_schedule_event.save()

        # create an event with two scheduled instances
        # one instance is before the test event and one instance is afterwards
        split_scheduled_event = Event.objects.create(
            title='Split Scheduled Event',
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=60,
            user=self.user
        )
        split_scheduled_event.save()

        early_schedule_event = ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=split_scheduled_event,
            placed_start=timezone.make_aware(self.today + timedelta(hours=1)),
            placed_end=timezone.make_aware(self.today + timedelta(hours=2)),
            status=ScheduleEvent.Status.SCHEDULED
        )
        early_schedule_event.save()

        late_schedule_event = ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=split_scheduled_event,
            placed_start=timezone.make_aware(self.today + timedelta(hours=4)),
            placed_end=timezone.make_aware(self.today + timedelta(hours=5)),
            status=ScheduleEvent.Status.SCHEDULED
        )
        late_schedule_event.save()

        # sorting by next scheduled occurrence should put the split scheduled event before the test event and exclude the expired event
        response = self._test_event_card_sequence_and_return_response('?sort=next_scheduled',
                                                                      [
                                                                          'Split Scheduled Event',
                                                                          'Test Event'])
        self._test_advanced_sorting_fixtures(response=response)
        self.assertNotContains(response, 'Expired Event')

    def test_filtering(self):
        self.log_in()

        # create two new events, one with category "Education" and one with category "Work"
        education_event = Event.objects.create(
            title='Education Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Education'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        education_event.save()

        work_event = Event.objects.create(
            title='Work Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Work'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        work_event.save()

        # response should only have work event
        response = self.client.get(self.url + '?filter=Work')
        self.assertContains(response, 'Work Event')
        self.assertNotContains(response, 'Education Event')
        self.assertNotContains(response, 'Test Event')

        # response should have work event and education event
        response = self.client.get(self.url + '?filter=Work&filter=Education')
        self.assertContains(response, 'Work Event')
        self.assertContains(response, 'Education Event')
        self.assertNotContains(response, 'Test Event')

    def test_search(self):
        self.log_in()

        # create an event with a specific name
        specific_name_event = Event.objects.create(
            title='Specifically Named Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        specific_name_event.save()

        # response should only contain the specifically named event
        response = self.client.get(self.url + '?query=specific')
        self.assertContains(response, 'Specifically Named Event')
        self.assertNotContains(response, 'Test Event')

    def test_pagination_divides_list_correctly(self):
        self.log_in()
        for i in range(39):
            new_event = Event.objects.create(
                title=f'Extra Event {i+1}',
                start=timezone.make_aware(self.today + timedelta(hours=2)),
                end=timezone.make_aware(self.today + timedelta(hours=4)),
                category=Category.objects.get(name='Other'),
                importance=Event.Priority.MEDIUM,
                duration=120,
                user=self.user
            )
            new_event.save()
        # page 1 should contain exactly 30 elements
        response = self.client.get(self.url + '?page=1')
        self.assertEqual(len(response.context.get('events')), 30)
        # url with no page parameters should show page 1
        response = self.client.get(self.url)
        self.assertEqual(len(response.context.get('events')), 30)
        # page 2 should contain exactly 10 elements
        response = self.client.get(self.url + '?page=2')
        self.assertEqual(len(response.context.get('events')), 10)
        # pages going over should be last page
        response = self.client.get(self.url + '?page=3')
        self.assertEqual(len(response.context.get('events')), 10)

    def log_in(self):
        self.client.login(username=self.user.username, password='Password123')

    def create_advanced_sorting_fixtures(self):
        # create event that is not in a schedule
        isolated_event = Event.objects.create(
            title='Isolated Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        isolated_event.save()

        # create event this is in a schedule but not marked as scheduled
        unscheduled_event = Event.objects.create(
            title='Unscheduled Event',
            start=timezone.make_aware(self.today + timedelta(hours=2)),
            end=timezone.make_aware(self.today + timedelta(hours=4)),
            category=Category.objects.get(name='Other'),
            importance=Event.Priority.MEDIUM,
            duration=120,
            user=self.user
        )
        unscheduled_event.save()
        unscheduled_schedule_event = ScheduleEvent.objects.create(
            schedule=self.schedule,
            event=unscheduled_event,
            placed_start=unscheduled_event.start,
            placed_end=unscheduled_event.end,
            status=ScheduleEvent.Status.CREATED
        )
        unscheduled_schedule_event.save()

    def _test_advanced_sorting_fixtures(self, response):
        # this response should not include the isolated or unscheduled events
        self.assertNotContains(response, 'Isolated Event')
        self.assertNotContains(response, 'Unscheduled Event')

    def _test_event_card_sequence_and_return_response(self, url_parameters, title_sequence):
        response = self.client.get(self.url + url_parameters)
        event_list = response.context.get('events')
        for i in range(len(title_sequence)):
            self.assertEqual(event_list[i].title, title_sequence[i])
        return response