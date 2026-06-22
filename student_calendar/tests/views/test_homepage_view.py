from django.test import TestCase
from django.urls import reverse
from student_calendar.models import User

class HomePageViewTestCase(TestCase):
    """Test case for the homepage view"""

    fixtures = ['student_calendar/tests/fixtures/default_user.json']

    def setUp(self):
        self.url = reverse('home')
        self.user = User.objects.get(username='exampleuser')

    def test_default_url(self):
        self.assertEqual(self.url, '/')

    def test_get_homepage(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage.html')

    def test_redirects_when_logged_in(self):
        self.client.login(username=self.user.username, password='Password123')
        response = self.client.get(self.url, follow=True)
        redirect_url = reverse('main_page')
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'main_page.html')
