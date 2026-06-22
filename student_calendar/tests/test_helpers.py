# Khan - tests for helpers.py (annotate_event_counters)

from django.test import TestCase

from student_calendar.models import (
    User, Event, Category, Schedule, ScheduleEvent, UserSchedule
)
from student_calendar.helpers import annotate_event_counters


class AnnotateEventCountersTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="pass123"
        )
        self.category = Category.objects.create(name="Study", colour="#0000FF")
        self.schedule = Schedule.objects.create(title="My Schedule", is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

        self.event = Event.objects.create(
            title="Gym", user=self.user, category=self.category,
            duration=60, importance=3,
            number_of_days=1, repeat_days=1, max_instances=4,
        )

    def _create_instance(self, status, index):
        return ScheduleEvent.objects.create(
            event=self.event, schedule=self.schedule,
            status=status, occurrence_index=index,
        )

    def test_counts_created(self):
        self._create_instance(ScheduleEvent.Status.CREATED, 1)
        self._create_instance(ScheduleEvent.Status.CREATED, 2)
        events = annotate_event_counters(Event.objects.filter(id=self.event.id))
        self.assertEqual(events.first().created_count, 2)

    def test_counts_scheduled(self):
        self._create_instance(ScheduleEvent.Status.SCHEDULED, 1)
        events = annotate_event_counters(Event.objects.filter(id=self.event.id))
        self.assertEqual(events.first().scheduled_count, 1)

    def test_counts_completed(self):
        self._create_instance(ScheduleEvent.Status.COMPLETED, 1)
        self._create_instance(ScheduleEvent.Status.COMPLETED, 2)
        self._create_instance(ScheduleEvent.Status.COMPLETED, 3)
        events = annotate_event_counters(Event.objects.filter(id=self.event.id))
        self.assertEqual(events.first().completed_count, 3)

    def test_counts_missed(self):
        self._create_instance(ScheduleEvent.Status.MISSED, 1)
        events = annotate_event_counters(Event.objects.filter(id=self.event.id))
        self.assertEqual(events.first().missed_count, 1)

    def test_no_instances_returns_zero(self):
        events = annotate_event_counters(Event.objects.filter(id=self.event.id))
        e = events.first()
        self.assertEqual(e.created_count, 0)
        self.assertEqual(e.scheduled_count, 0)
        self.assertEqual(e.completed_count, 0)
        self.assertEqual(e.missed_count, 0)

    def test_mixed_statuses_counted_separately(self):
        self._create_instance(ScheduleEvent.Status.CREATED, 1)
        self._create_instance(ScheduleEvent.Status.SCHEDULED, 2)
        self._create_instance(ScheduleEvent.Status.COMPLETED, 3)
        self._create_instance(ScheduleEvent.Status.MISSED, 4)
        events = annotate_event_counters(Event.objects.filter(id=self.event.id))
        e = events.first()
        self.assertEqual(e.created_count, 1)
        self.assertEqual(e.scheduled_count, 1)
        self.assertEqual(e.completed_count, 1)
        self.assertEqual(e.missed_count, 1)

    def test_counts_scoped_to_specific_event(self):
        # create a second event with its own instances
        other_event = Event.objects.create(
            title="Study", user=self.user, category=self.category,
            duration=90, importance=4, number_of_days=1, repeat_days=1,
        )
        self._create_instance(ScheduleEvent.Status.COMPLETED, 1)
        ScheduleEvent.objects.create(
            event=other_event, schedule=self.schedule,
            status=ScheduleEvent.Status.COMPLETED, occurrence_index=1,
        )

        events = annotate_event_counters(
            Event.objects.filter(id__in=[self.event.id, other_event.id])
        )
        gym = events.get(title="Gym")
        study = events.get(title="Study")
        # each should have 1, not 2
        self.assertEqual(gym.completed_count, 1)
        self.assertEqual(study.completed_count, 1)
