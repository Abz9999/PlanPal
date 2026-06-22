from datetime import datetime
from django.test import TestCase
from student_calendar.forms import CreateEvent
from student_calendar.models import Event, Category, User


class CreateEventFormTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            password='Password123!'
        )
        self.category = Category.objects.create(name='Test Category', colour='#FF5733')
        # Default: Case 1 — full start + end date/time
        self.form_input = {
            'title': 'Test Event',
            'category': self.category.pk,
            'start_date': '2026-06-01',
            'start_time': '09:00',
            'end_date': '2026-06-01',
            'end_time': '11:00',
            'number_of_days': 1,
            'repeat_days': ['1'],   # MON bitmask value
            'repeat_weeks': 1,
            'location': 'London',
            'description': 'Test description',
            'importance': Event.Priority.HIGH,
        }

    def assert_form_is_valid(self):
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def assert_form_is_invalid(self):
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertFalse(form.is_valid())

    # ====================
    # Default Test
    # ====================

    def test_default_form_is_valid(self):
        self.assert_form_is_valid()

    def test_form_has_all_required_fields(self):
        form = CreateEvent(user=self.user)
        for field in [
            'title', 'start_date', 'start_time', 'end_date', 'end_time',
            'duration', 'hours', 'minutes', 'repeat_days', 'number_of_days',
            'repeat_weeks', 'location', 'description', 'category', 'importance',
        ]:
            self.assertIn(field, form.fields)

    # ====================
    # Title Tests
    # ====================

    def test_blank_title_is_invalid(self):
        self.form_input['title'] = ''
        self.assert_form_is_invalid()

    def test_title_may_be_50_characters_long(self):
        self.form_input['title'] = 'x' * 50
        self.assert_form_is_valid()

    def test_title_must_not_exceed_50_characters(self):
        self.form_input['title'] = 'x' * 51
        self.assert_form_is_invalid()

    # ====================
    # Category Tests
    # ====================

    def test_category_is_required(self):
        del self.form_input['category']
        self.assert_form_is_invalid()

    # ====================
    # Location / Description Tests
    # ====================

    def test_blank_location_is_valid(self):
        self.form_input['location'] = ''
        self.assert_form_is_valid()

    def test_blank_description_is_valid(self):
        self.form_input['description'] = ''
        self.assert_form_is_valid()

    # ====================
    # Date / Time Case Tests
    # ====================

    # Case 1: full start+end date and time
    def test_full_start_and_end_sets_correct_datetimes(self):
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['start'], datetime(2026, 6, 1, 9, 0))
        self.assertEqual(form.cleaned_data['end'],   datetime(2026, 6, 1, 11, 0))

    def test_full_start_and_end_derives_correct_duration(self):
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['duration'], 120)

    # Case 2: start date+time + explicit duration, no end
    def test_start_with_hours_and_no_end_is_valid(self):
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.form_input['hours'] = 1
        self.form_input['minutes'] = 30
        self.assert_form_is_valid()

    def test_start_with_no_end_and_no_duration_is_invalid(self):
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.assert_form_is_invalid()

    # Case 3: no dates at all, duration only
    def test_no_dates_with_hours_only_is_valid(self):
        del self.form_input['start_date']
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.form_input['hours'] = 2
        self.assert_form_is_valid()

    def test_no_dates_and_no_duration_is_invalid(self):
        del self.form_input['start_date']
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.assert_form_is_invalid()

    def test_no_dates_hours_and_minutes_give_correct_duration(self):
        del self.form_input['start_date']
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.form_input['hours'] = 1
        self.form_input['minutes'] = 30
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['duration'], 90)

    # Case 4: start date only (no time), duration
    def test_start_date_only_with_duration_is_valid(self):
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.form_input['hours'] = 1
        self.assert_form_is_valid()

    def test_start_date_only_without_duration_is_invalid(self):
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.assert_form_is_invalid()

    # Case 5: time only (no date), stored on sentinel date
    def test_time_only_no_date_is_valid(self):
        del self.form_input['start_date']
        del self.form_input['end_date']
        self.assert_form_is_valid()

    def test_time_only_with_end_before_start_is_invalid(self):
        del self.form_input['start_date']
        del self.form_input['end_date']
        self.form_input['end_time'] = '08:00'  # before start_time 09:00
        self.assert_form_is_invalid()

    def test_time_only_with_equal_start_and_end_is_invalid(self):
        del self.form_input['start_date']
        del self.form_input['end_date']
        self.form_input['end_time'] = '09:00'  # same as start_time
        self.assert_form_is_invalid()

    # ====================
    # Hours / Minutes Tests
    # ====================

    def test_hours_above_23_is_invalid(self):
        self.form_input['hours'] = 24
        self.assert_form_is_invalid()

    def test_hours_at_max_23_is_valid(self):
        del self.form_input['start_date']
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.form_input['hours'] = 23
        self.assert_form_is_valid()

    def test_minutes_above_59_is_invalid(self):
        self.form_input['minutes'] = 60
        self.assert_form_is_invalid()

    def test_minutes_at_max_59_is_valid(self):
        del self.form_input['start_date']
        del self.form_input['start_time']
        del self.form_input['end_date']
        del self.form_input['end_time']
        self.form_input['minutes'] = 59
        self.assert_form_is_valid()

    def test_negative_hours_is_invalid(self):
        self.form_input['hours'] = -1
        self.assert_form_is_invalid()

    def test_negative_minutes_is_invalid(self):
        self.form_input['minutes'] = -1
        self.assert_form_is_invalid()

    # ====================
    # Repeat Days Tests
    # ====================

    def test_no_days_selected_sets_repeat_days_to_zero(self):
        self.form_input['repeat_days'] = []
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['repeat_days'], 0)

    def _strip_case1_dates(self):
        # Case 1 events (full start+end date+time) force repeat_days to 0 and
        # days/weeks to 1 since they're one-offs. These tests exercise the
        # bitmask summation itself, so swap the default Case 1 input for a
        # Case 3 (duration only) setup where repeat fields stay editable.
        for f in ['start_date', 'start_time', 'end_date', 'end_time']:
            self.form_input.pop(f, None)
        self.form_input['hours'] = 1
        self.form_input['minutes'] = 0

    def test_single_day_selection_sets_correct_bitmask(self):
        self._strip_case1_dates()
        self.form_input['repeat_days'] = ['1']  # MON = 1
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['repeat_days'], 1)

    def test_multiple_days_selection_sums_bitmasks(self):
        self._strip_case1_dates()
        self.form_input['repeat_days'] = ['1', '2']  # MON(1) + TUE(2) = 3
        self.form_input['number_of_days'] = 2
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['repeat_days'], 3)

    def test_all_days_selected_gives_full_bitmask(self):
        self._strip_case1_dates()
        self.form_input['repeat_days'] = ['1', '2', '4', '8', '16', '32', '64']
        self.form_input['number_of_days'] = 7
        form = CreateEvent(data=self.form_input, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['repeat_days'], 127)

    # ====================
    # Importance Tests
    # ====================

    def test_each_valid_priority_value_is_valid(self):
        for priority in Event.Priority:
            self.form_input['importance'] = priority.value
            self.assert_form_is_valid()

    def test_invalid_importance_value_is_invalid(self):
        self.form_input['importance'] = 99
        self.assert_form_is_invalid()
