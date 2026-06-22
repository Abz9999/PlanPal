# Khan - tests for event_instances.py endpoints

import json
from datetime import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from student_calendar.models import (
    User, Event, Category, Schedule, ScheduleEvent, UserSchedule
)


class EventInstancesSetUp(TestCase):
    """shared setUp for all event instance tests"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="pass123"
        )
        self.client.login(username="testuser", password="pass123")

        self.category = Category.objects.create(name="Study", colour="#0000FF")
        self.schedule = Schedule.objects.create(title="My Schedule", is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

        # event with 3 instances
        self.event = Event.objects.create(
            title="Gym", user=self.user, category=self.category,
            duration=60, importance=3,
            number_of_days=1, repeat_days=1, max_instances=3,
        )
        for i in range(3):
            ScheduleEvent.objects.create(
                event=self.event, schedule=self.schedule,
                status=ScheduleEvent.Status.CREATED,
                occurrence_index=i + 1,
            )

        # another user for permission tests
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@test.com", password="pass123"
        )
        self.other_schedule = Schedule.objects.create(title="Other Schedule")
        UserSchedule.objects.create(user=self.other_user, schedule=self.other_schedule)
        self.other_event = Event.objects.create(
            title="Not Mine", user=self.other_user, category=self.category,
            duration=30, importance=1, number_of_days=1, repeat_days=1,
        )
        self.other_instance = ScheduleEvent.objects.create(
            event=self.other_event, schedule=self.other_schedule,
            status=ScheduleEvent.Status.CREATED, occurrence_index=1,
        )


# ---- get_event_instances tests ----

class GetEventInstancesTests(EventInstancesSetUp):

    def test_returns_instances_for_event(self):
        url = reverse('event_instances', args=[self.event.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['instances']), 3)

    def test_instances_ordered_by_occurrence_index(self):
        url = reverse('event_instances', args=[self.event.pk])
        response = self.client.get(url)
        data = response.json()
        indexes = [inst['occurrence_index'] for inst in data['instances']]
        self.assertEqual(indexes, [1, 2, 3])

    def test_instance_has_required_fields(self):
        url = reverse('event_instances', args=[self.event.pk])
        response = self.client.get(url)
        data = response.json()
        inst = data['instances'][0]
        self.assertIn('id', inst)
        self.assertIn('occurrence_index', inst)
        self.assertIn('status', inst)
        self.assertIn('placed_start', inst)
        self.assertIn('placed_end', inst)

    def test_response_has_event_info(self):
        url = reverse('event_instances', args=[self.event.pk])
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data['event_id'], self.event.id)
        self.assertEqual(data['title'], 'Gym')
        self.assertEqual(data['max_instances'], 3)

    def test_other_users_event_returns_404(self):
        url = reverse('event_instances', args=[self.other_event.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_requires_login(self):
        self.client.logout()
        url = reverse('event_instances', args=[self.event.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


# ---- update_instance_status tests ----

class UpdateInstanceStatusTests(EventInstancesSetUp):

    def _get_instance(self):
        return ScheduleEvent.objects.filter(event=self.event).first()

    def _get_scheduled_instance(self):
        # Helper: return an instance that's already been placed on the schedule
        # (status=SCHEDULED with placed times). Used for tests that set status
        # to COMPLETED or MISSED, which are only allowed from SCHEDULED.
        inst = self._get_instance()
        inst.status = ScheduleEvent.Status.SCHEDULED
        inst.placed_start = timezone.make_aware(datetime(2026, 4, 13, 9, 0))
        inst.placed_end = timezone.make_aware(datetime(2026, 4, 13, 10, 0))
        inst.save()
        return inst

    def test_set_status_completed(self):
        inst = self._get_scheduled_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 3}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.COMPLETED)

    def test_set_status_missed(self):
        inst = self._get_scheduled_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 4}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.MISSED)

    def test_cannot_mark_created_as_completed(self):
        # An instance that's only CREATED (not placed on calendar) shouldn't be
        # allowed to jump straight to COMPLETED - that caused the bug where the
        # completed page showed instances that were never scheduled.
        inst = self._get_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 3}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.CREATED)

    def test_cannot_mark_created_as_missed(self):
        inst = self._get_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 4}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.CREATED)

    def test_set_status_scheduled(self):
        inst = self._get_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 2}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.SCHEDULED)

    def test_other_users_instance_returns_403(self):
        url = reverse('update_instance_status', args=[self.other_instance.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 3}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_status_returns_400(self):
        inst = self._get_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 99}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_get_request_returns_400(self):
        inst = self._get_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        inst = self._get_instance()
        url = reverse('update_instance_status', args=[inst.pk])
        response = self.client.post(
            url, data=json.dumps({'status': 3}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)


# ---- unplace_instance tests ----

class UnplaceInstanceTests(EventInstancesSetUp):

    def test_clears_placement_and_resets_status(self):
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        # first place it
        inst.status = ScheduleEvent.Status.SCHEDULED
        inst.placed_start = timezone.make_aware(datetime(2026, 4, 13, 9, 0))
        inst.placed_end = timezone.make_aware(datetime(2026, 4, 13, 10, 0))
        inst.save()

        url = reverse('unplace_instance', args=[inst.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.CREATED)
        self.assertIsNone(inst.placed_start)
        self.assertIsNone(inst.placed_end)

    def test_other_users_instance_returns_403(self):
        url = reverse('unplace_instance', args=[self.other_instance.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_get_request_returns_400(self):
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        url = reverse('unplace_instance', args=[inst.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_cannot_unplace_completed_instance(self):
        # Completed instances are historical — unplacing them would silently
        # flip their status back to CREATED and lose the completion record.
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        inst.status = ScheduleEvent.Status.COMPLETED
        inst.save()
        url = reverse('unplace_instance', args=[inst.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.COMPLETED)

    def test_cannot_unplace_missed_instance(self):
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        inst.status = ScheduleEvent.Status.MISSED
        inst.save()
        url = reverse('unplace_instance', args=[inst.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.MISSED)

    def test_requires_login(self):
        self.client.logout()
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        url = reverse('unplace_instance', args=[inst.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)


# ---- place_instance tests ----

class PlaceInstanceTests(EventInstancesSetUp):

    def test_places_instance_with_times(self):
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        url = reverse('place_instance', args=[inst.pk])
        response = self.client.post(
            url,
            data=json.dumps({
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.status, ScheduleEvent.Status.SCHEDULED)
        self.assertIsNotNone(inst.placed_start)
        self.assertIsNotNone(inst.placed_end)

    def test_missing_placed_start_returns_400(self):
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        url = reverse('place_instance', args=[inst.pk])
        response = self.client.post(
            url,
            data=json.dumps({'placed_end': '2026-04-13T10:00:00'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_other_users_instance_returns_403(self):
        url = reverse('place_instance', args=[self.other_instance.pk])
        response = self.client.post(
            url,
            data=json.dumps({
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_get_request_returns_400(self):
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        url = reverse('place_instance', args=[inst.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        inst = ScheduleEvent.objects.filter(event=self.event).first()
        url = reverse('place_instance', args=[inst.pk])
        response = self.client.post(
            url,
            data=json.dumps({
                'placed_start': '2026-04-13T09:00:00',
                'placed_end': '2026-04-13T10:00:00',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)
