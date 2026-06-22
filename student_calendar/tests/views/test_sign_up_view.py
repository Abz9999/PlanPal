from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.urls import reverse
from student_calendar.models import User
from student_calendar.forms import SignUpForm
from student_calendar.tests.test_utility import LogInTester

class SignUpViewTestCase(TestCase, LogInTester):
    """Test case for the sign up view"""

    fixtures = ['student_calendar/tests/fixtures/default_user.json']

    def setUp(self):
        self.url = reverse('sign_up')
        self.form_input = {
            'first_name': 'Another',
            'last_name': 'User',
            'username': 'otheruser',
            'email': 'other@user.org',
            'new_password': 'password',
            'confirm_password': 'password'
        }
        self.user = User.objects.get(username='exampleuser')

    def test_url(self):
        self.assertEqual(self.url, '/sign_up/')

    def test_sign_up(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'signup.html')
        form = response.context.get('form')
        self.assertTrue(isinstance(form, SignUpForm))
        self.assertFalse(form.is_bound)

    def test_sign_up_redirects_when_logged_in(self):
        self.client.login(username=self.user.username, password='Password123')
        response = self.client.get(self.url, follow=True)
        redirect = reverse('main_page')
        self.assertRedirects(response, redirect, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'main_page.html')

    def test_successful_sign_up(self):
        before = User.objects.count()
        response = self.client.post(self.url, self.form_input)
        after = User.objects.count()
        self.assertEqual(before+1, after)
        response_url = reverse('main_page')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        user = User.objects.get(username='otheruser')
        self.assertEqual(user.first_name, 'Another')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'other@user.org')
        password_correct = check_password('password', user.password)
        self.assertTrue(password_correct)
        self.assertTrue(self._is_logged_in())

    def test_failed_sign_up(self):
        self.form_input['username'] = 'no'
        before = User.objects.count()
        response = self.client.post(self.url, self.form_input)
        after = User.objects.count()
        self.assertEqual(before, after)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'signup.html')
        form = response.context.get('form')
        self.assertTrue(isinstance(form, SignUpForm))
        self.assertTrue(form.is_bound)
        self.assertFalse(self._is_logged_in())

    def test_post_sign_up_redirects_logged_in(self):
        self.client.login(username=self.user.username, password='Password123')
        before = User.objects.count()
        response = self.client.post(self.url, self.form_input, follow=True)
        after = User.objects.count()
        self.assertEqual(before, after)
        redirect = reverse('main_page')
        self.assertRedirects(response, redirect, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'main_page.html')