# Khan - tests for the smart planner view endpoints

import json
from datetime import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from student_calendar.models import (
    User, Event, Category, Schedule, ScheduleEvent, UserSchedule
)


class SmartPlannerViewSetUp(TestCase):
    """shared setUp for all smart planner view tests"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testplanner", email="planner@test.com", password="pass123"
        )
        self.client.login(username="testplanner", password="pass123")

        self.category = Category.objects.create(name="Study", colour="#0000FF")
        self.schedule = Schedule.objects.create(title="My Schedule", is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

        # flexible event with 2 CREATED instances
        self.flex_event = Event.objects.create(
            title="Gym", user=self.user, category=self.category,
            duration=60, importance=3,
            number_of_days=1, repeat_days=1, max_instances=2,
        )
        for i in range(2):
            ScheduleEvent.objects.create(
                event=self.flex_event, schedule=self.schedule,
                status=ScheduleEvent.Status.CREATED,
                occurrence_index=i + 1,
            )

        # fixed event with 1 CREATED instance
        self.fixed_event = Event.objects.create(
            title="Lecture", user=self.user, category=self.category,
            start=timezone.make_aware(datetime(2026, 4, 13, 9, 0)),
            end=timezone.make_aware(datetime(2026, 4, 13, 10, 0)),
            importance=5, number_of_days=1, repeat_days=1, max_instances=1,
        )
        ScheduleEvent.objects.create(
            event=self.fixed_event, schedule=self.schedule,
            status=ScheduleEvent.Status.CREATED,
            occurrence_index=1,
        )

        # valid constraints for generate endpoint
        self.valid_constraints = {
            'start_date': '2026-04-13',
            'end_date': '2026-04-17',
            'day_start': '08:00',
            'day_end': '18:00',
            'selected_days_bitmask': 31,
            'buffer_minutes': 0,
            'keep_or_erase': 'keep',
        }


# ---- get_smart_planner_events tests ----

class GetSmartPlannerEventsTests(SmartPlannerViewSetUp):

    def setUp(self):
        super().setUp()
        self.url = reverse('smart_plan_events')

    def test_returns_json_with_events(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('events', data)
        self.assertGreater(len(data['events']), 0)

    def test_events_belong_to_user(self):
        # create another user with their own event
        other_user = User.objects.create_user(
            username="other", email="other@test.com", password="pass123"
        )
        Event.objects.create(
            title="Other Event", user=other_user, category=self.category,
            duration=30, importance=1, number_of_days=1, repeat_days=1,
        )
        response = self.client.get(self.url)
        data = response.json()
        titles = [e['title'] for e in data['events']]
        self.assertNotIn("Other Event", titles)

    def test_event_has_required_fields(self):
        response = self.client.get(self.url)
        data = response.json()
        event = data['events'][0]
        # check all the fields the JS needs
        self.assertIn('id', event)
        self.assertIn('title', event)
        self.assertIn('duration_minutes', event)
        self.assertIn('duration_display', event)
        self.assertIn('is_fixed', event)
        self.assertIn('category_name', event)
        self.assertIn('category_colour', event)
        self.assertIn('created_count', event)
        self.assertIn('scheduled_count', event)
        self.assertIn('completed_count', event)
        self.assertIn('missed_count', event)

    def test_flexible_event_has_correct_flags(self):
        response = self.client.get(self.url)
        data = response.json()
        gym = next(e for e in data['events'] if e['title'] == 'Gym')
        self.assertFalse(gym['is_fixed'])
        self.assertEqual(gym['duration_minutes'], 60)

    def test_fixed_event_has_correct_flags(self):
        response = self.client.get(self.url)
        data = response.json()
        lecture = next(e for e in data['events'] if e['title'] == 'Lecture')
        self.assertTrue(lecture['is_fixed'])
        self.assertEqual(lecture['duration_minutes'], 60)

    def test_counters_are_correct(self):
        response = self.client.get(self.url)
        data = response.json()
        gym = next(e for e in data['events'] if e['title'] == 'Gym')
        self.assertEqual(gym['created_count'], 2)
        self.assertEqual(gym['scheduled_count'], 0)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        # should redirect to login page
        self.assertEqual(response.status_code, 302)


# ---- generate_smart_plan tests ----

class GenerateSmartPlanTests(SmartPlannerViewSetUp):

    def setUp(self):
        super().setUp()
        self.url = reverse('smart_plan_generate')

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_valid_request_returns_plan(self):
        payload = {
            'constraints': self.valid_constraints,
            'selected_template_ids': [self.flex_event.id],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('placed', data)
        self.assertIn('unplaced', data)
        self.assertIn('summary', data)
        self.assertIn('weeks', data)

    def test_missing_constraint_returns_400(self):
        # leave out start_date
        bad_constraints = dict(self.valid_constraints)
        del bad_constraints['start_date']
        payload = {
            'constraints': bad_constraints,
            'selected_template_ids': [self.flex_event.id],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_no_templates_returns_400(self):
        payload = {
            'constraints': self.valid_constraints,
            'selected_template_ids': [],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)

    def test_get_request_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url,
            data="not valid json{{{",
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        payload = {
            'constraints': self.valid_constraints,
            'selected_template_ids': [self.flex_event.id],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 302)

    def test_placed_events_have_start_and_end(self):
        payload = {
            'constraints': self.valid_constraints,
            'selected_template_ids': [self.flex_event.id],
        }
        response = self._post(payload)
        data = response.json()
        for item in data['placed']:
            self.assertIn('placed_start', item)
            self.assertIn('placed_end', item)

    def test_summary_counts_match(self):
        payload = {
            'constraints': self.valid_constraints,
            'selected_template_ids': [self.flex_event.id],
        }
        response = self._post(payload)
        data = response.json()
        summary = data['summary']
        self.assertEqual(summary['total_placed'], len(data['placed']))
        self.assertEqual(summary['total_unplaced'], len(data['unplaced']))


# ---- confirm_smart_plan tests ----

class ConfirmSmartPlanTests(SmartPlannerViewSetUp):

    def setUp(self):
        super().setUp()
        self.url = reverse('smart_plan_confirm')

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_valid_confirm_sets_status_scheduled(self):
        instance = ScheduleEvent.objects.filter(
            event=self.flex_event
        ).first()
        payload = {
            'placed': [{
                'schedule_event_id': instance.id,
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }],
            'unplaced': [],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        # check the DB was actually updated
        instance.refresh_from_db()
        self.assertEqual(instance.status, ScheduleEvent.Status.SCHEDULED)
        self.assertIsNotNone(instance.placed_start)
        self.assertIsNotNone(instance.placed_end)

    def test_unplaced_items_reset_to_created(self):
        # first schedule an instance
        instance = ScheduleEvent.objects.filter(
            event=self.flex_event
        ).first()
        instance.status = ScheduleEvent.Status.SCHEDULED
        instance.placed_start = timezone.make_aware(datetime(2026, 4, 13, 9, 0))
        instance.placed_end = timezone.make_aware(datetime(2026, 4, 13, 10, 0))
        instance.save()

        # get a different instance to put in placed (need at least one)
        other_instance = ScheduleEvent.objects.filter(
            event=self.flex_event
        ).exclude(id=instance.id).first()

        payload = {
            'placed': [{
                'schedule_event_id': other_instance.id,
                'placed_start': '2026-04-14T09:00:00',
                'placed_end': '2026-04-14T10:00:00',
            }],
            'unplaced': [{
                'schedule_event_id': instance.id,
            }],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        instance.refresh_from_db()
        self.assertEqual(instance.status, ScheduleEvent.Status.CREATED)
        self.assertIsNone(instance.placed_start)

    def test_wrong_user_returns_403(self):
        # create another user and try to confirm their instance
        other_user = User.objects.create_user(
            username="hacker", email="hack@test.com", password="pass123"
        )
        other_schedule = Schedule.objects.create(title="Other Schedule")
        UserSchedule.objects.create(user=other_user, schedule=other_schedule)
        other_event = Event.objects.create(
            title="Not Mine", user=other_user, category=self.category,
            duration=60, importance=3, number_of_days=1, repeat_days=1,
        )
        other_instance = ScheduleEvent.objects.create(
            event=other_event, schedule=other_schedule,
            status=ScheduleEvent.Status.CREATED, occurrence_index=1,
        )
        payload = {
            'placed': [{
                'schedule_event_id': other_instance.id,
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }],
            'unplaced': [],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 403)

    def test_empty_placed_returns_400(self):
        payload = {'placed': [], 'unplaced': []}
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)

    def test_get_request_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url,
            data="broken json!!!",
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        instance = ScheduleEvent.objects.filter(event=self.flex_event).first()
        payload = {
            'placed': [{
                'schedule_event_id': instance.id,
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }],
            'unplaced': [],
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 302)


    def test_placed_count_in_response(self):
        instance = ScheduleEvent.objects.filter(event=self.flex_event).first()
        payload = {
            'placed': [{
                'schedule_event_id': instance.id,
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }],
            'unplaced': [],
        }
        response = self._post(payload)
        data = response.json()
        self.assertEqual(data['placed_count'], 1)
