from django.core.exceptions import ValidationError
from django.test import TestCase
from student_calendar.models import User

class UserModelTestCase(TestCase):
    """Unit tests for the User model"""

    fixtures = [
        'student_calendar/tests/fixtures/default_user.json',
        'student_calendar/tests/fixtures/other_users.json'
    ]

    def setUp(self):
        self.user = User.objects.get(username='exampleuser')

    def assert_user_is_valid(self):
        try:
            self.user.full_clean()
        except ValidationError:
            self.fail('Test user should be valid')

    def assert_user_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_valid_user(self):
        self.assert_user_is_valid()

    # username tests

    def test_username_must_not_be_blank(self):
        self.user.username = ''
        self.assert_user_is_invalid()

    def test_username_may_be_30_characters_long(self):
        self.user.username = 'x' * 30
        self.assert_user_is_valid()

    def test_username_must_not_be_overlong(self):
        self.user.username = 'x' * 31
        self.assert_user_is_invalid()

    def test_username_must_not_be_too_short(self):
        self.user.username = 'xy'
        self.assert_user_is_invalid()

    def test_username_must_be_unique(self):
        other_user = User.objects.get(username='exampleuser2')
        self.user.username = other_user.username
        self.assert_user_is_invalid()

    def test_username_must_only_contain_alphanumerical_characters(self):
        self.user.username = 'examp!euser'
        self.assert_user_is_invalid()

    def test_username_may_contain_numbers(self):
        self.user.username = '3xampleuser'
        self.assert_user_is_valid()

    # first name tests

    def test_first_name_must_not_be_blank(self):
        self.user.first_name = ''
        self.assert_user_is_invalid()

    def test_first_name_may_be_not_unique(self):
        other_user = User.objects.get(username='exampleuser2')
        self.user.first_name = other_user.first_name
        self.assert_user_is_valid()

    def test_first_name_may_contain_50_characters(self):
        self.user.first_name = 'x' * 50
        self.assert_user_is_valid()

    def test_first_name_must_not_be_overlong(self):
        self.user.first_name = 'x' * 51
        self.assert_user_is_invalid()

    # last name tests

    def test_last_name_must_not_be_blank(self):
        self.user.last_name = ''
        self.assert_user_is_invalid()

    def test_last_name_may_be_not_unique(self):
        other_user = User.objects.get(username='exampleuser2')
        self.user.last_name = other_user.last_name
        self.assert_user_is_valid()

    def test_last_name_may_contain_50_characters(self):
        self.user.last_name = 'x' * 50
        self.assert_user_is_valid()

    def test_last_name_must_not_be_overlong(self):
        self.user.last_name = 'x' * 51
        self.assert_user_is_invalid()

    # email tests

    def test_email_must_not_be_blank(self):
        self.user.email = ''
        self.assert_user_is_invalid()

    def test_email_must_be_unique(self):
        other_user = User.objects.get(username='exampleuser2')
        self.user.email = other_user.email
        self.assert_user_is_invalid()

    def test_email_must_contain_username(self):
        self.user.email = '@example.org'
        self.assert_user_is_invalid()

    def test_email_must_contain_at_symbol(self):
        self.user.email = 'example.example.org'
        self.assert_user_is_invalid()

    def test_email_must_contain_domain_name(self):
        self.user.email = 'example@.org'
        self.assert_user_is_invalid()

    def test_email_must_contain_tld(self):
        self.user.email = 'example@example'
        self.assert_user_is_invalid()

    def test_email_must_contain_only_one_at_symbol(self):
        self.user.email = 'example@@example.org'
        self.assert_user_is_invalid()