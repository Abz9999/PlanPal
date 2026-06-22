from django.test import TestCase
from django.urls import reverse
from student_calendar.models import User, Event, Category, Schedule, ScheduleEvent, UserSchedule


class CreateEventViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        self.category = Category.objects.create(
            name="Study",
            colour="#FF0000"
        )

        self.client.login(username="testuser", password="password123")

        self.url = reverse("create_event")
        self.main_page_url = reverse("main_page")

    def test_create_flexible_event_creates_correct_number_of_schedule_events(self):
        response = self.client.post(self.url, {
            "title": "Flexible Gym",
            "start_date": "",
            "start_time": "",
            "end_date": "",
            "end_time": "",
            "hours": 1,
            "minutes": 0,
            "number_of_days": 2,
            "repeat_days": [],
            "repeat_weeks": 2,
            "category": self.category.id,
            "importance": Event.Priority.MEDIUM,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.main_page_url)

        event = Event.objects.get(title="Flexible Gym")
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.duration, 60)
        self.assertEqual(event.repeat_days, 0)
        self.assertEqual(event.number_of_days, 2)
        self.assertEqual(event.repeat_weeks, 2)
        self.assertEqual(event.max_instances, 4)

        schedule_events = ScheduleEvent.objects.filter(event=event).order_by("occurrence_index")
        self.assertEqual(schedule_events.count(), 4)

        for i, se in enumerate(schedule_events, start=1):
            self.assertEqual(se.occurrence_index, i)
            self.assertEqual(se.status, ScheduleEvent.Status.CREATED)
            self.assertIsNone(se.placed_start)
            self.assertIsNone(se.placed_end)
            self.assertEqual(se.placed_by, self.user)

    def test_create_repeating_event_creates_correct_number_of_schedule_events(self):
        response = self.client.post(self.url, {
            "title": "Lecture",
            "start_date": "",
            "start_time": "09:00",
            "end_date": "",
            "end_time": "10:00",
            "hours": "",
            "minutes": "",
            "number_of_days": 2,
            "repeat_days": ["1", "2"],
            "repeat_weeks": 2,
            "category": self.category.id,
            "importance": Event.Priority.HIGH,
            "location": "Room 101",
            "description": "Weekly lectures",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.main_page_url)

        event = Event.objects.get(title="Lecture")
        self.assertEqual(event.repeat_days, Event.MON | Event.TUE)
        self.assertEqual(event.number_of_days, 2)
        self.assertEqual(event.repeat_weeks, 2)
        self.assertEqual(event.max_instances, 4)

        schedule_events = ScheduleEvent.objects.filter(event=event).order_by("occurrence_index")
        self.assertEqual(schedule_events.count(), 4)

        for i, se in enumerate(schedule_events, start=1):
            self.assertEqual(se.occurrence_index, i)
            self.assertEqual(se.status, ScheduleEvent.Status.CREATED)
            self.assertEqual(se.placed_by, self.user)
            self.assertIsNotNone(se.placed_start)
            self.assertIsNotNone(se.placed_end)

    def test_fixed_repeating_event_occurrences_keep_time_of_day(self):
        response = self.client.post(self.url, {
            "title": "Seminar",
            "start_date": "",
            "start_time": "10:30",
            "end_date": "",
            "end_time": "12:00",
            "hours": "",
            "minutes": "",
            "number_of_days": 2,
            "repeat_days": ["1", "4"],
            "repeat_weeks": 2,
            "category": self.category.id,
            "importance": Event.Priority.MEDIUM,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)

        event = Event.objects.get(title="Seminar")
        schedule_events = ScheduleEvent.objects.filter(event=event).order_by("occurrence_index")

        self.assertEqual(schedule_events.count(), 4)

        for se in schedule_events:
            self.assertIsNotNone(se.placed_start)
            self.assertIsNotNone(se.placed_end)

    def test_schedule_is_created_if_user_has_no_schedule(self):
        self.assertFalse(UserSchedule.objects.filter(user=self.user).exists())

        response = self.client.post(self.url, {
            "title": "Create Schedule Test",
            "start_date": "",
            "start_time": "",
            "end_date": "",
            "end_time": "",
            "hours": 0,
            "minutes": 45,
            "number_of_days": 1,
            "repeat_days": [],
            "repeat_weeks": 1,
            "category": self.category.id,
            "importance": Event.Priority.LOW,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserSchedule.objects.filter(user=self.user).exists())

        user_schedule = UserSchedule.objects.get(user=self.user)
        self.assertIsInstance(user_schedule.schedule, Schedule)

        event = Event.objects.get(title="Create Schedule Test")
        schedule_event = ScheduleEvent.objects.get(event=event)
        self.assertEqual(schedule_event.schedule, user_schedule.schedule)

    def test_existing_schedule_is_reused(self):
        schedule = Schedule.objects.create(
            title="Existing Schedule",
            is_active=True
        )
        UserSchedule.objects.create(user=self.user, schedule=schedule)

        response = self.client.post(self.url, {
            "title": "Reuse Schedule Test",
            "start_date": "",
            "start_time": "",
            "end_date": "",
            "end_time": "",
            "hours": 0,
            "minutes": 30,
            "number_of_days": 1,
            "repeat_days": [],
            "repeat_weeks": 1,
            "category": self.category.id,
            "importance": Event.Priority.LOW,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserSchedule.objects.filter(user=self.user).count(), 1)

        event = Event.objects.get(title="Reuse Schedule Test")
        schedule_event = ScheduleEvent.objects.get(event=event)
        self.assertEqual(schedule_event.schedule, schedule)

    def test_occurrence_indexes_are_sequential_for_flexible_event(self):
        response = self.client.post(self.url, {
            "title": "Occurrence Order Test",
            "start_date": "",
            "start_time": "",
            "end_date": "",
            "end_time": "",
            "hours": 2,
            "minutes": 0,
            "number_of_days": 2,
            "repeat_days": [],
            "repeat_weeks": 3,
            "category": self.category.id,
            "importance": Event.Priority.MEDIUM,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)

        event = Event.objects.get(title="Occurrence Order Test")
        occurrences = list(
            ScheduleEvent.objects.filter(event=event)
            .order_by("occurrence_index")
            .values_list("occurrence_index", flat=True)
        )

        self.assertEqual(occurrences, [1, 2, 3, 4, 5, 6])

    def test_occurrence_indexes_are_sequential_for_repeating_event(self):
        response = self.client.post(self.url, {
            "title": "Repeating Occurrence Order Test",
            "start_date": "",
            "start_time": "08:00",
            "end_date": "",
            "end_time": "09:00",
            "hours": "",
            "minutes": "",
            "number_of_days": 3,
            "repeat_days": ["1", "2", "4"],
            "repeat_weeks": 2,
            "category": self.category.id,
            "importance": Event.Priority.MEDIUM,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 302)

        event = Event.objects.get(title="Repeating Occurrence Order Test")
        occurrences = list(
            ScheduleEvent.objects.filter(event=event)
            .order_by("occurrence_index")
            .values_list("occurrence_index", flat=True)
        )

        self.assertEqual(occurrences, [1, 2, 3, 4, 5, 6])

    def test_invalid_form_does_not_create_event(self):
        response = self.client.post(self.url, {
            "title": "",
            "start_date": "",
            "start_time": "",
            "end_date": "",
            "end_time": "",
            "hours": "",
            "minutes": "",
            "number_of_days": 0,
            "repeat_days": [],
            "repeat_weeks": 0,
            "category": "",
            "importance": Event.Priority.MEDIUM,
            "location": "",
            "description": "",
            "next": self.main_page_url,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(ScheduleEvent.objects.count(), 0)


class CreateEventViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('create_event')
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            password='Password123!'
        )
        self.category = Category.objects.get(name='Other')
        self.form_input = {
            'title': 'New Event',
            'category': self.category.pk,
            'start_date': '2026-06-01',
            'start_time': '09:00',
            'end_date': '2026-06-01',
            'end_time': '11:00',
            'number_of_days': 1,
            'repeat_days': ['1'],   # MON
            'repeat_weeks': 1,
            'location': '',
            'description': '',
            'importance': Event.Priority.MEDIUM,
        }

    def log_in(self):
        self.client.login(username='testuser', password='Password123!')

    # ====================
    # URL Test
    # ====================

    def test_url(self):
        self.assertEqual(self.url, '/create_event/')

    # ====================
    # Auth Tests
    # ====================

    def test_get_redirects_when_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_redirects_when_not_logged_in(self):
        response = self.client.post(self.url, self.form_input)
        self.assertEqual(response.status_code, 302)

    # ====================
    # GET Tests
    # ====================

    def test_get_returns_200(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_uses_correct_template(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'partials/create_event.html')

    def test_get_renders_form_in_context(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertIn('form', response.context)

    # ====================
    # POST (valid) Tests
    # ====================

    def test_valid_post_creates_event(self):
        self.log_in()
        count_before = Event.objects.count()
        self.client.post(self.url, self.form_input)
        self.assertEqual(Event.objects.count(), count_before + 1)

    def test_valid_post_assigns_event_to_logged_in_user(self):
        self.log_in()
        self.client.post(self.url, self.form_input)
        event = Event.objects.get(title='New Event')
        self.assertEqual(event.user, self.user)

    def test_valid_post_redirects(self):
        self.log_in()
        response = self.client.post(self.url, self.form_input)
        self.assertEqual(response.status_code, 302)

    def test_valid_post_creates_schedule_event_instances(self):
        self.log_in()
        self.client.post(self.url, self.form_input)
        event = Event.objects.get(title='New Event')
        self.assertEqual(ScheduleEvent.objects.filter(event=event).count(), event.max_instances)

    def test_valid_post_creates_schedule_if_none_exists(self):
        self.log_in()
        self.assertEqual(UserSchedule.objects.filter(user=self.user).count(), 0)
        self.client.post(self.url, self.form_input)
        self.assertGreater(UserSchedule.objects.filter(user=self.user).count(), 0)

    def test_valid_post_uses_existing_active_schedule(self):
        schedule = Schedule.objects.create(title='Existing Schedule', is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=schedule)
        self.log_in()
        self.client.post(self.url, self.form_input)
        self.assertEqual(UserSchedule.objects.filter(user=self.user).count(), 1)

    def test_max_instances_is_days_times_weeks(self):
        # Case 1 events (full start+end) are one-offs so days/weeks force to 1.
        # This test checks the days*weeks multiplication, so use Case 3 (no dates).
        for f in ['start_date', 'start_time', 'end_date', 'end_time']:
            self.form_input.pop(f, None)
        self.form_input['hours'] = 1
        self.form_input['minutes'] = 0
        self.form_input['repeat_days'] = ['1', '2']  # MON + TUE
        self.form_input['number_of_days'] = 2
        self.form_input['repeat_weeks'] = 3
        self.log_in()
        self.client.post(self.url, self.form_input)
        event = Event.objects.get(title='New Event')
        self.assertEqual(event.max_instances, 6)

    def test_next_parameter_redirects_correctly(self):
        self.log_in()
        response = self.client.post(self.url + '?next=dashboard', self.form_input)
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

    # ====================
    # POST (invalid) Tests
    # ====================

    def test_invalid_post_does_not_create_event(self):
        self.log_in()
        self.form_input['title'] = ''
        count_before = Event.objects.count()
        self.client.post(self.url, self.form_input)
        self.assertEqual(Event.objects.count(), count_before)

    def test_invalid_post_returns_200(self):
        self.log_in()
        self.form_input['title'] = ''
        response = self.client.post(self.url, self.form_input)
        self.assertEqual(response.status_code, 200)
