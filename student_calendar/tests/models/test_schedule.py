# Created by Theodore Tsiberopoulos
from django.test import TestCase
from student_calendar.models import Schedule
from django.core.exceptions import ValidationError

class ScheduleModelTestCase(TestCase):
    """Unit tests for the Schedule model"""
    def setUp(self):
        title = 'Test Schedule'
        self.schedule = Schedule(title=title)

    def assert_schedule_is_valid(self):
        try:
            self.schedule.full_clean()
        except ValidationError:
            self.fail('Test Schedule should be valid')

    def assert_schedule_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.schedule.full_clean()

    def test_valid_schedule(self):
        self.assert_schedule_is_valid()

    # title tests

    def test_title_must_not_be_blank(self):
        self.schedule.title = ''
        self.assert_schedule_is_invalid()

    def test_title_may_be_100_characters_long(self):
        self.schedule.title = 'x' * 100
        self.assert_schedule_is_valid()

    def test_title_must_not_be_overlong(self):
        self.schedule.title = 'x' * 101
        self.assert_schedule_is_invalid()

    # is_active tests

    def test_is_active_defaults_to_false(self):
        self.assertFalse(self.schedule.is_active)

    def test_is_active_can_be_set_to_true(self):
        self.schedule.is_active = True
        self.assert_schedule_is_valid()
