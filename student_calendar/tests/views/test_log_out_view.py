from django.test import TestCase
from django.urls import reverse
from student_calendar.models import User
from student_calendar.tests.test_utility import LogInTester

class LogOutViewTestCase(TestCase, LogInTester):
    """Test case for the log out view"""

    fixtures = ['student_calendar/tests/fixtures/default_user.json']

    def setUp(self):
        self.url = reverse('log_out')
        self.user = User.objects.get(username='exampleuser')

    def test_url(self):
        self.assertEqual(self.url, '/log_out/')

    def test_get_log_out(self):
        self.client.login(username='exampleuser', password='Password123')
        self.assertTrue(self._is_logged_in())
        response = self.client.get(self.url, follow=True)
        response_url = reverse('home')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'homepage.html')
        self.assertFalse(self._is_logged_in())

    def test_get_log_out_when_not_logged_in(self):
        response = self.client.get(self.url, follow=True)
        response_url = reverse('home')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'homepage.html')
        self.assertFalse(self._is_logged_in())
