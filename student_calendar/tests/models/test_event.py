from django.test import TestCase
from student_calendar.models import Event, Category, User
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError


class EventModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            password='Password123!'
        )
        self.category = Category.objects.create(name='Test Category', colour='#FF5733')
        self.today = timezone.now()
        self.event = Event(
            title='Test Event',
            start=self.today,
            end=self.today + timedelta(hours=2),
            location='London',
            description='This is a test event',
            category=self.category,
            importance=Event.Priority.HIGH,
            number_of_days=1,
            repeat_days=Event.MON,
            repeat_weeks=1,
            user=self.user
        )

    def assert_event_is_valid(self):
        try:
            self.event.full_clean()
        except ValidationError:
            self.fail('Test event should be valid')

    def assert_event_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.event.full_clean()

    # ====================
    # Default Test
    # ====================

    def test_default_event_is_valid(self):
        self.assert_event_is_valid()

    # ====================
    # Title Tests
    # ====================

    def test_title_must_not_be_blank(self):
        self.event.title = ''
        self.assert_event_is_invalid()

    def test_title_may_be_50_characters_long(self):
        self.event.title = 'x' * 50
        self.assert_event_is_valid()

    def test_title_must_not_exceed_50_characters(self):
        self.event.title = 'x' * 51
        self.assert_event_is_invalid()

    # ====================
    # Location Tests
    # ====================

    def test_blank_location_is_valid(self):
        self.event.location = ''
        self.assert_event_is_valid()

    def test_location_may_be_255_characters_long(self):
        self.event.location = 'x' * 255
        self.assert_event_is_valid()

    def test_location_must_not_exceed_255_characters(self):
        self.event.location = 'x' * 256
        self.assert_event_is_invalid()

    # ====================
    # Description Tests
    # ====================

    def test_blank_description_is_valid(self):
        self.event.description = ''
        self.assert_event_is_valid()

    # ====================
    # Start / End Validation
    # ====================

    def test_start_without_end_and_no_duration_is_invalid(self):
        self.event.end = None
        self.event.duration = None
        self.assert_event_is_invalid()

    def test_end_without_start_is_invalid(self):
        self.event.start = None
        self.assert_event_is_invalid()

    def test_end_before_start_is_invalid(self):
        self.event.end = self.today - timedelta(hours=1)
        self.assert_event_is_invalid()

    def test_end_equal_to_start_is_invalid(self):
        self.event.end = self.today
        self.assert_event_is_invalid()

    # ====================
    # Duration Tests
    # ====================

    def test_event_without_start_end_but_with_duration_is_valid(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = 60
        self.assert_event_is_valid()

    def test_duration_required_when_no_start_or_end(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = None
        self.assert_event_is_invalid()

    def test_zero_duration_without_start_end_is_invalid(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = 0
        self.assert_event_is_invalid()

    def test_negative_duration_without_start_end_is_invalid(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = -30
        self.assert_event_is_invalid()

    def test_duration_is_derived_from_start_and_end(self):
        self.event.duration = None
        self.event.full_clean()
        expected = max(1, int((self.event.end - self.event.start).total_seconds() // 60))
        self.assertEqual(self.event.duration, expected)

    # ====================
    # Repeat Weeks Tests
    # ====================

    def test_repeat_weeks_of_one_is_valid(self):
        self.event.repeat_weeks = 1
        self.assert_event_is_valid()

    def test_repeat_weeks_of_zero_is_invalid(self):
        self.event.repeat_weeks = 0
        self.assert_event_is_invalid()

    def test_negative_repeat_weeks_is_invalid(self):
        self.event.repeat_weeks = -1
        self.assert_event_is_invalid()

    # ====================
    # Number of Days Tests
    # ====================

    def test_number_of_days_of_one_is_valid(self):
        self.event.number_of_days = 1
        self.event.repeat_days = Event.MON
        self.assert_event_is_valid()

    def test_number_of_days_of_seven_is_valid(self):
        self.event.number_of_days = 7
        self.event.repeat_days = (
            Event.MON | Event.TUE | Event.WED |
            Event.THU | Event.FRI | Event.SAT | Event.SUN
        )
        self.assert_event_is_valid()

    def test_number_of_days_of_zero_is_invalid(self):
        self.event.number_of_days = 0
        self.assert_event_is_invalid()

    def test_number_of_days_of_eight_is_invalid(self):
        self.event.number_of_days = 8
        self.assert_event_is_invalid()

    # ====================
    # Repeat Days Tests
    # ====================

    def test_repeat_days_bit_count_must_match_number_of_days(self):
        self.event.number_of_days = 2
        self.event.repeat_days = Event.MON  # only 1 bit set but number_of_days=2
        self.assert_event_is_invalid()

    def test_repeat_days_with_correct_bit_count_is_valid(self):
        self.event.number_of_days = 2
        self.event.repeat_days = Event.MON | Event.TUE
        self.assert_event_is_valid()

    def test_repeat_days_bitmask_above_max_is_invalid(self):
        self.event.repeat_days = 128  # exceeds 7-bit max (127)
        self.assert_event_is_invalid()

    def test_negative_repeat_days_is_invalid(self):
        self.event.repeat_days = -1
        self.assert_event_is_invalid()

    # ====================
    # Importance Tests
    # ====================

    def test_invalid_importance_value_is_invalid(self):
        self.event.importance = 99
        self.assert_event_is_invalid()

    def test_all_valid_priority_values_are_valid(self):
        for priority in Event.Priority:
            self.event.importance = priority.value
            self.assert_event_is_valid()

    # ====================
    # Helper Method Tests
    # ====================

    def test_get_repeat_days_returns_correct_list(self):
        self.event.repeat_days = Event.MON | Event.WED
        self.event.number_of_days = 2
        result = self.event.get_repeat_days()
        self.assertEqual(result, ['Mon', 'Wed'])

    def test_get_repeat_days_display_returns_comma_separated_string(self):
        self.event.repeat_days = Event.MON | Event.WED
        self.event.number_of_days = 2
        result = self.event.get_repeat_days_display()
        self.assertEqual(result, 'Mon, Wed')

    def test_str_contains_event_title(self):
        self.assertIn(self.event.title, str(self.event))

    # ====================
    # Duration Format Tests
    # ====================

    def test_duration_format_minutes_only(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = 45
        self.assertEqual(self.event.duration_format(), '45 mins')

    def test_duration_format_one_hour(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = 60
        self.assertEqual(self.event.duration_format(), '1 hr')

    def test_duration_format_multiple_hours(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = 120
        self.assertEqual(self.event.duration_format(), '2 hrs')

    def test_duration_format_hours_and_minutes(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = 90
        self.assertEqual(self.event.duration_format(), '1 hr 30 mins')

    def test_duration_format_with_no_duration_set(self):
        self.event.start = None
        self.event.end = None
        self.event.duration = None
        self.assertEqual(self.event.duration_format(), 'no duration set')
