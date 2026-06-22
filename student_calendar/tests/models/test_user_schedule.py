# Created by Theodore Tsiberopoulos
from django.test import TestCase
from django.core.exceptions import ValidationError
from student_calendar.models import User, Schedule, UserSchedule


class UserScheduleModelTestCase(TestCase):
    """Unit tests for the UserSchedule model"""
    fixtures = [
        'student_calendar/tests/fixtures/default_user.json'
    ]

    def setUp(self):
        self.user = User.objects.get(username='exampleuser')

        self.schedule = Schedule(title='Test Schedule')
        self.schedule.save()

        self.user_schedule = UserSchedule(
            user=self.user,
            schedule=self.schedule
        )

    def assert_user_schedule_is_valid(self):
        try:
            self.user_schedule.full_clean()
        except:
            self.fail('Test User Schedule should be valid')

    def assert_user_schedule_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.user_schedule.full_clean()

    # validation test

    def test_valid_user_schedule(self):
        self.assert_user_schedule_is_valid()

    # user tests

    def test_user_must_not_be_blank(self):
        self.user_schedule.user = None
        self.assert_user_schedule_is_invalid()

    def test_user_must_be_user(self):
        with self.assertRaises(ValueError):
            self.user_schedule.user = 'user'

    # schedule tests

    def test_schedule_must_not_be_blank(self):
        self.user_schedule.schedule = None
        self.assert_user_schedule_is_invalid()

    def test_schedule_must_be_schedule(self):
        with self.assertRaises(ValueError):
            self.user_schedule.schedule = 'schedule'