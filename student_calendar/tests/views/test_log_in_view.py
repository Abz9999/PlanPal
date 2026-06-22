from django.test import TestCase
from django.urls import reverse
from django.contrib import messages
from student_calendar.models import User
from student_calendar.forms import LogInForm
from student_calendar.tests.test_utility import LogInTester, MenuTesterMixin, reverse_next


class LogInViewTestCase(TestCase, LogInTester, MenuTesterMixin):
    """Test case for the log in view"""

    fixtures = ['student_calendar/tests/fixtures/default_user.json']

    def setUp(self):
        self.url = reverse('log_in')
        self.user = User.objects.get(username='exampleuser')

    def test_url(self):
        self.assertEqual(self.url, '/log_in/')

    def test_log_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        form = response.context.get('form')
        response_next = response.context.get('next')
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)
        self.assertFalse(response_next)
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 0)
        self.assert_not_menu(response)

    def test_log_in_redirect(self):
        target = reverse('main_page')
        self.url = reverse_next('log_in', target)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        form = response.context.get('form')
        response_next = response.context.get('next')
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)
        self.assertEqual(response_next, target)
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 0)

    def test_log_in_redirects_when_logged_in(self):
        self.client.login(username=self.user.username, password='Password123')
        response = self.client.get(self.url, follow=True)
        redirect = reverse('main_page')
        self.assertRedirects(response, redirect, status_code=302, target_status_code=200)

    def test_failed_log_in(self):
        form_input = {'username': 'exampleuser', 'password': 'badpassword'}
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        form = response.context.get('form')
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)
        self.assertFalse(self._is_logged_in())
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(messages_list[0].level, messages.ERROR)

    def test_log_in_no_username(self):
        form_input = {'username': '', 'password': 'Password123'}
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        form = response.context.get('form')
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)
        self.assertFalse(self._is_logged_in())
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(messages_list[0].level, messages.ERROR)

    def test_log_in_no_password(self):
        form_input = {'username': 'exampleuser', 'password': ''}
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        form = response.context.get('form')
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)
        self.assertFalse(self._is_logged_in())
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(messages_list[0].level, messages.ERROR)

    def test_log_in_success(self):
        form_input = {'username': 'exampleuser', 'password': 'Password123'}
        response = self.client.post(self.url, form_input, follow=True)
        self.assertTrue(self._is_logged_in())
        url_response = reverse('main_page')
        self.assertRedirects(response, url_response, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'main_page.html')
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 0)
        self.assert_menu(response)

    def test_log_in_success_redirect(self):
        redirect = reverse('main_page')
        form_input = {'username': 'exampleuser', 'password': 'Password123', 'next': redirect}
        response = self.client.post(self.url, form_input, follow=True)
        self.assertTrue(self._is_logged_in())
        self.assertRedirects(response, redirect, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'main_page.html')
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 0)

    def test_post_log_in_redirects_when_logged_in(self):
        self.client.login(username=self.user.username, password='Password123')
        form_input = {'username': 'badusername', 'password': 'badpassword'}
        response = self.client.post(self.url, form_input, follow=True)
        redirect = reverse('main_page')
        self.assertRedirects(response, redirect, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'main_page.html')

    def test_post_log_in_bad_info_and_redirect(self):
        redirect = reverse('main_page')
        form_input = {'username': 'exampleuser', 'password': 'badpassword', 'next': redirect}
        response = self.client.post(self.url, form_input)
        response_next = response.context.get('next')
        self.assertEqual(response_next, redirect)

    def test_log_in_while_inactive(self):
        self.user.is_active = False
        self.user.save()
        form_input = {'username': 'exampleuser', 'password': 'Password123'}
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'log_in.html')
        form = response.context.get('form')
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)
        self.assertFalse(self._is_logged_in())
        messages_list = list(response.context.get('messages'))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(messages_list[0].level, messages.ERROR)
