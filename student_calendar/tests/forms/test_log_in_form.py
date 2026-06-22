from django import forms
from django.test import TestCase
from student_calendar.forms import LogInForm
from student_calendar.models import User


class LogInFormTestCase(TestCase):
    """Unit tests for the log-in form"""

    fixtures = ['student_calendar/tests/fixtures/default_user.json']

    def setUp(self):
        self.form_input = {
            'username': 'exampleuser',
            'password': 'Password123'
        }

    def test_form_contains_required_fields(self):
        form = LogInForm()
        self.assertIn('username', form.fields)
        self.assertIn('password', form.fields)
        password_widget = form.fields['password'].widget
        self.assertTrue(isinstance(password_widget, forms.PasswordInput))

    def test_valid_log_in_form(self):
        form = LogInForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_blank_username_is_invalid(self):
        self.form_input['username'] = ''
        form = LogInForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_blank_password_is_invalid(self):
        self.form_input['password'] = ''
        form = LogInForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_wrong_username_is_valid(self):
        self.form_input['username'] = 'someoneelse'
        form = LogInForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_wrong_password_is_valid(self):
        self.form_input['password'] = 'otherpassword'
        form = LogInForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_can_authenticate_correct_user(self):
        fixture = User.objects.get(username='exampleuser')
        form_input = {'username': 'exampleuser', 'password': 'Password123'}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, fixture)

    def test_cannot_authenticate_wrong_user(self):
        form_input = {'username': 'exampleuser', 'password': 'badpassword'}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, None)

    def test_cannot_authenticate_blank_username(self):
        form_input = {'username': '', 'password': 'Password123'}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, None)

    def test_cannot_authenticate_blank_password(self):
        form_input = {'username': 'exampleuser', 'password': ''}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, None)
