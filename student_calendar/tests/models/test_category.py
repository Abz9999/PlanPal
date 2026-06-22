from django.test import TestCase
from student_calendar.models import Category
from django.core.exceptions import ValidationError


class CategoryModelTestCase(TestCase):

    def setUp(self):
        self.category = Category(name='Lecture', colour='#FF5733')

    def assert_category_is_valid(self):
        try:
            self.category.full_clean()
        except ValidationError:
            self.fail('Test category should be valid')

    def assert_category_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.category.full_clean()

    # ====================
    # Default Test
    # ====================

    def test_default_category_is_valid(self):
        self.assert_category_is_valid()

    # ====================
    # Name Tests
    # ====================

    def test_name_must_not_be_blank(self):
        self.category.name = ''
        self.assert_category_is_invalid()

    def test_name_may_be_50_characters_long(self):
        self.category.name = 'x' * 50
        self.assert_category_is_valid()

    def test_name_must_not_exceed_50_characters(self):
        self.category.name = 'x' * 51
        self.assert_category_is_invalid()

    def test_name_must_be_unique(self):
        self.category.save()
        duplicate = Category(name='Lecture', colour='#00FF00')
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    # ====================
    # Colour Tests
    # ====================

    def test_valid_uppercase_hex_colour_is_valid(self):
        self.category.colour = '#1A2B3C'
        self.assert_category_is_valid()

    def test_valid_lowercase_hex_colour_is_valid(self):
        self.category.colour = '#aabbcc'
        self.assert_category_is_valid()

    def test_colour_without_hash_is_invalid(self):
        self.category.colour = 'FF5733'
        self.assert_category_is_invalid()

    def test_colour_with_invalid_characters_is_invalid(self):
        self.category.colour = '#GGGGGG'
        self.assert_category_is_invalid()

    def test_colour_shorthand_hex_is_invalid(self):
        self.category.colour = '#FFF'
        self.assert_category_is_invalid()

    def test_blank_colour_is_invalid(self):
        self.category.colour = ''
        self.assert_category_is_invalid()

    def test_colour_as_plain_word_is_invalid(self):
        self.category.colour = 'red'
        self.assert_category_is_invalid()

    # ====================
    # String Representation
    # ====================

    def test_str_returns_category_name(self):
        self.assertEqual(str(self.category), 'Lecture')
