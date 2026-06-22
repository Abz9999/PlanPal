import json
from django.test import TestCase
from django.urls import reverse
from student_calendar.models import User, Schedule, UserSchedule


class GetSchedulesViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('get_schedules')
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            password='Password123!'
        )
        self.schedule = Schedule.objects.create(title='My Schedule', is_active=True)
        UserSchedule.objects.create(user=self.user, schedule=self.schedule)

    def log_in(self):
        self.client.login(username='testuser', password='Password123!')

    def post_json(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )

    # ====================
    # URL Test
    # ====================

    def test_url(self):
        self.assertEqual(self.url, '/api/schedules/')

    # ====================
    # Auth Tests
    # ====================

    def test_get_redirects_when_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_redirects_when_not_logged_in(self):
        response = self.post_json({'title': 'New Schedule'})
        self.assertEqual(response.status_code, 302)

    # ====================
    # GET Tests
    # ====================

    def test_get_returns_200(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_returns_json(self):
        self.log_in()
        response = self.client.get(self.url)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_get_returns_users_schedules(self):
        self.log_in()
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(len(data['schedules']), 1)
        self.assertEqual(data['schedules'][0]['title'], 'My Schedule')

    def test_get_returns_correct_schedule_fields(self):
        self.log_in()
        response = self.client.get(self.url)
        schedule_data = json.loads(response.content)['schedules'][0]
        self.assertIn('id', schedule_data)
        self.assertIn('title', schedule_data)
        self.assertIn('is_active', schedule_data)

    def test_get_does_not_return_other_users_schedules(self):
        other_user = User.objects.create_user(
            username='otheruser',
            first_name='Other',
            last_name='User',
            email='other@example.com',
            password='Password123!'
        )
        other_schedule = Schedule.objects.create(title='Other Schedule')
        UserSchedule.objects.create(user=other_user, schedule=other_schedule)
        self.log_in()
        response = self.client.get(self.url)
        titles = [s['title'] for s in json.loads(response.content)['schedules']]
        self.assertNotIn('Other Schedule', titles)

    def test_get_returns_empty_list_when_no_schedules(self):
        UserSchedule.objects.filter(user=self.user).delete()
        self.schedule.delete()
        self.log_in()
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(data['schedules'], [])

    # ====================
    # POST (valid) Tests
    # ====================

    def test_post_returns_201(self):
        self.log_in()
        response = self.post_json({'title': 'New Schedule'})
        self.assertEqual(response.status_code, 201)

    def test_post_creates_schedule_linked_to_user(self):
        self.log_in()
        self.post_json({'title': 'New Schedule'})
        self.assertTrue(
            UserSchedule.objects.filter(user=self.user, schedule__title='New Schedule').exists()
        )

    def test_post_creates_schedule_as_not_active(self):
        self.log_in()
        response = self.post_json({'title': 'New Schedule'})
        self.assertFalse(json.loads(response.content)['is_active'])

    def test_post_returns_schedule_data(self):
        self.log_in()
        response = self.post_json({'title': 'New Schedule'})
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'New Schedule')
        self.assertIn('id', data)

    # ====================
    # POST (invalid) Tests
    # ====================

    def test_post_with_missing_title_returns_400(self):
        self.log_in()
        response = self.post_json({})
        self.assertEqual(response.status_code, 400)

    def test_post_with_empty_title_returns_400(self):
        self.log_in()
        response = self.post_json({'title': '   '})
        self.assertEqual(response.status_code, 400)

    def test_post_with_duplicate_title_returns_400(self):
        self.log_in()
        response = self.post_json({'title': 'My Schedule'})
        self.assertEqual(response.status_code, 400)

    def test_post_with_duplicate_title_is_case_insensitive(self):
        self.log_in()
        response = self.post_json({'title': 'MY SCHEDULE'})
        self.assertEqual(response.status_code, 400)

    def test_post_with_invalid_json_returns_400(self):
        self.log_in()
        response = self.client.post(self.url, data='not valid json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    # ====================
    # Method Tests
    # ====================

    def test_delete_method_not_allowed(self):
        self.log_in()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 405)
