from django import forms
from django.test import TestCase
from student_calendar.forms import SignUpForm
from student_calendar.forms import User
from django.contrib.auth.hashers import check_password


class SignUpFormTestCase(TestCase):
    """Unit tests for the sign-up form"""

    def setUp(self):
        self.form_input = {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testuser',
            'email': 'example@user.org',
            'new_password': 'password',
            'confirm_password': 'password'
        }

    def test_valid_sign_up_form(self):
        form = SignUpForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_form_has_all_fields(self):
        form = SignUpForm()
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)
        self.assertIn('username', form.fields)
        self.assertIn('email', form.fields)
        email_field = form.fields['email']
        self.assertTrue(isinstance(email_field, forms.EmailField))
        self.assertIn('new_password', form.fields)
        password_widget = form.fields['new_password'].widget
        self.assertTrue(isinstance(password_widget, forms.PasswordInput))
        self.assertIn('confirm_password', form.fields)
        password_confirm_widget = form.fields['confirm_password'].widget
        self.assertTrue(isinstance(password_confirm_widget, forms.PasswordInput))

    def test_form_uses_model_validation(self):
        self.form_input['username'] = 'no'
        form = SignUpForm(data=self.form_input)
        self.assertFalse(form.is_valid())
        self.form_input['username'] = 'badu$ername'
        form = SignUpForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_password_must_not_be_too_short(self):
        self.form_input['new_password'] = 'small'
        self.form_input['confirm_password'] = 'small'
        form = SignUpForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_password_and_confirm_identical(self):
        self.form_input['confirm_password'] = 'badpassword'
        form = SignUpForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_form_must_save_correctly(self):
        old_count = User.objects.count()
        form = SignUpForm(data=self.form_input)
        form.save()
        new_count = User.objects.count()
        self.assertEqual(new_count, old_count + 1)
        user = User.objects.get(username='testuser')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'example@user.org')
        password_correct = check_password('password', user.password)
        self.assertTrue(password_correct)
