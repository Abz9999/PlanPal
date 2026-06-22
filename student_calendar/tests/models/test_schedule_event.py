# Created by Theodore Tsiberopoulos
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from student_calendar.models import ScheduleEvent, Schedule, Event, User, Category
from datetime import datetime, timedelta


class ScheduleEventModelTestCase(TestCase):
    """Unit tests for the ScheduleEvent model"""
    fixtures = [
        'student_calendar/tests/fixtures/default_user.json'
    ]
    def setUp(self):
        self.today = datetime.now()

        self.user = User.objects.get(username='exampleuser')

        self.event = Event(
            title='Test Event',
            start=timezone.make_aware(self.today),
            end=timezone.make_aware(self.today + timedelta(hours=2)),
            repeat_days=0,
            duration=2,
            repeat_weeks=0,
            category=Category.objects.get(name='Other'),
            user=self.user
        )
        self.event.save()

        self.schedule = Schedule(title='Test Schedule')
        self.schedule.save()

        self.schedule_event = ScheduleEvent(
            schedule=self.schedule,
            event=self.event,
            placed_start=timezone.make_aware(self.today),
            placed_end=timezone.make_aware(self.today + timedelta(hours=2)),
            status=ScheduleEvent.Status.CREATED,
            placed_by=self.user
        )

    def assert_schedule_event_is_valid(self):
        try:
            self.schedule_event.full_clean()
        except ValidationError:
            self.fail('Test Schedule Event should be valid')

    def assert_schedule_event_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.schedule_event.full_clean()

    # validation tests

    def test_valid_schedule_event(self):
        self.assert_schedule_event_is_valid()

    def test_placed_start_after_placed_end_is_invalid(self):
        self.schedule_event.placed_start = timezone.make_aware(self.today + timedelta(hours=4))
        self.assert_schedule_event_is_invalid()

    # schedule tests

    def test_schedule_must_not_be_blank(self):
        self.schedule_event.schedule = None
        self.assert_schedule_event_is_invalid()

    def test_schedule_must_be_schedule(self):
        with self.assertRaises(ValueError):
            self.schedule_event.schedule = 'schedule'

    # event tests

    def test_event_must_not_be_blank(self):
        self.schedule_event.event = None
        self.assert_schedule_event_is_invalid()

    def test_event_must_be_event(self):
        with self.assertRaises(ValueError):
            self.schedule_event.event = 'event'

    # start and end time tests

    def test_start_time_may_be_blank(self):
        self.schedule_event.placed_start = None
        self.assert_schedule_event_is_valid()

    def test_end_time_may_be_blank(self):
        self.schedule_event.placed_end = None
        self.assert_schedule_event_is_valid()

    def test_end_time_must_be_after_start_time(self):
        self.schedule_event.placed_end = timezone.make_aware(self.today - timedelta(hours=2))
        self.assert_schedule_event_is_invalid()

    # status and placed by tests

    def test_status_must_not_be_blank(self):
        self.schedule_event.status = None
        self.assert_schedule_event_is_invalid()

    def test_placed_by_may_be_blank(self):
        self.schedule_event.placed_by = None
        self.assert_schedule_event_is_valid()

    def test_status_must_be_status_type(self):
        self.schedule_event.status = 'created'
        self.assert_schedule_event_is_invalid()

    def test_placed_by_must_be_user(self):
        with self.assertRaises(ValueError):
            self.schedule_event.placed_by = 'user'