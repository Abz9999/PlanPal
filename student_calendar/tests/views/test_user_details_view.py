# Created by Codex

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from student_calendar.forms.user_details_forms import PROFILE_PICTURE_MAX_SIZE

User = get_user_model()


def reverse_next(name, next_url):
    return f"{reverse(name)}?next={next_url}"


MINIMAL_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n'
    b'\x00\x00\x00\rIHDR'
    b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00'
    b'\x90wS\xde'
    b'\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00'
    b'\xc9\xfe\x92\xef'
    b'\x00\x00\x00\x00IEND\xaeB`\x82'
)
MINIMAL_GIF_BYTES = (
    b'GIF89a'
    b'\x01\x00\x01\x00'
    b'\x80\x00\x00'
    b'\x00\x00\x00'
    b'\xff\xff\xff'
    b'!\xf9\x04\x01\x00\x00\x00\x00'
    b',\x00\x00\x00\x00\x01\x00\x01\x00\x00'
    b'\x02\x02L\x01\x00;'
)


class UserDetailsViewTestCase(TestCase):
    fixtures = ['student_calendar/tests/fixtures/default_user.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media_dir = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_dir)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.url = reverse('user_details')
        self.user = User.objects.get(username='exampleuser')

    def _is_logged_in(self):
        return '_auth_user_id' in self.client.session.keys()

    def _make_uploaded_image(
        self,
        name='avatar.png',
        content=MINIMAL_PNG_BYTES,
        content_type='image/png',
    ):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def _make_oversized_image(self):
        oversized_content = MINIMAL_PNG_BYTES + (b'0' * PROFILE_PICTURE_MAX_SIZE)
        oversized_image = self._make_uploaded_image(
            name='oversized.png',
            content=oversized_content,
            content_type='image/png',
        )
        if oversized_image.size <= PROFILE_PICTURE_MAX_SIZE:
            self.fail('Failed to generate an oversized image fixture.')
        return oversized_image

    def test_url(self):
        self.assertEqual(self.url, '/user/details/')

    def test_get_requires_login(self):
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(
            response,
            reverse_next('log_in', self.url),
            status_code=302,
            target_status_code=200
        )
        self.assertTemplateUsed(response, 'log_in.html')

    def test_get_user_details(self):
        self.client.login(username='exampleuser', password='Password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_details.html')
        self.assertContains(response, 'exampleuser')
        self.assertContains(response, 'example@example.org')
        self.assertContains(response, 'Example')
        self.assertContains(response, 'User')

    def test_post_updates_user_details(self):
        self.client.login(username='exampleuser', password='Password123')
        form_input = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'username': 'exampleuser',
            'email': 'updated@example.org',
            'save_details': '1',
        }
        response = self.client.post(self.url, form_input, follow=True)
        self.assertRedirects(response, self.url, status_code=302, target_status_code=200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'updated@example.org')

    def test_post_invalid_update_shows_errors(self):
        self.client.login(username='exampleuser', password='Password123')
        form_input = {
            'first_name': 'Example',
            'last_name': 'User',
            'username': 'exampleuser',
            'email': 'not-an-email',
            'save_details': '1',
        }
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_details.html')
        self.assertTrue(response.context['user_form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'example@example.org')

    def test_post_delete_requires_confirmation(self):
        self.client.login(username='exampleuser', password='Password123')
        response = self.client.post(self.url, {'delete_account': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_details.html')
        self.assertTrue(response.context['delete_form'].errors)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_post_changes_password_and_keeps_session(self):
        self.client.login(username='exampleuser', password='Password123')
        form_input = {
            'old_password': 'Password123',
            'new_password1': 'StrongPass123$',
            'new_password2': 'StrongPass123$',
            'change_password': '1',
        }
        response = self.client.post(self.url, form_input, follow=True)
        self.assertRedirects(response, self.url, status_code=302, target_status_code=200)
        self.assertFalse(response.context['password_form'].errors)
        self.assertTrue(self._is_logged_in())
        self.client.logout()
        self.assertTrue(self.client.login(username='exampleuser', password='StrongPass123$'))

    def test_post_invalid_password_change_shows_errors(self):
        self.client.login(username='exampleuser', password='Password123')
        form_input = {
            'old_password': 'WrongPassword123',
            'new_password1': 'StrongPass123$',
            'new_password2': 'StrongPass123$',
            'change_password': '1',
        }
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_details.html')
        self.assertTrue(response.context['password_form'].errors)
        self.client.logout()
        self.assertTrue(self.client.login(username='exampleuser', password='Password123'))

    def test_post_uploads_valid_profile_picture(self):
        self.client.login(username='exampleuser', password='Password123')
        profile_picture = self._make_uploaded_image()
        response = self.client.post(
            self.url,
            {'profile_picture': profile_picture, 'save_profile_picture': '1'},
            follow=True
        )
        self.assertRedirects(response, self.url, status_code=302, target_status_code=200)
        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_picture))
        self.assertTrue(self.user.profile_picture.name.startswith('profile_pictures/'))
        self.assertContains(response, 'Using your uploaded profile picture.')
        self.assertContains(response, 'Remove Picture')

    def test_post_rejects_invalid_profile_picture_type(self):
        self.client.login(username='exampleuser', password='Password123')
        invalid_picture = self._make_uploaded_image(
            name='avatar.gif',
            content=MINIMAL_GIF_BYTES,
            content_type='image/gif',
        )
        response = self.client.post(
            self.url,
            {'profile_picture': invalid_picture, 'save_profile_picture': '1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_details.html')
        self.assertIn(
            'Upload a JPG, JPEG, PNG, or WEBP image.',
            response.context['profile_picture_form'].errors['profile_picture']
        )
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.profile_picture))

    def test_post_rejects_oversized_profile_picture(self):
        self.client.login(username='exampleuser', password='Password123')
        oversized_picture = self._make_oversized_image()
        self.assertGreater(oversized_picture.size, PROFILE_PICTURE_MAX_SIZE)
        response = self.client.post(
            self.url,
            {'profile_picture': oversized_picture, 'save_profile_picture': '1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_details.html')
        self.assertIn(
            'Profile picture must be 2 MB or smaller.',
            response.context['profile_picture_form'].errors['profile_picture']
        )
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.profile_picture))

    def test_post_remove_profile_picture_clears_picture(self):
        existing_picture = self._make_uploaded_image(name='existing.png')
        self.user.profile_picture.save(existing_picture.name, existing_picture, save=True)
        self.client.login(username='exampleuser', password='Password123')

        response = self.client.post(
            self.url,
            {'remove_profile_picture': '1'},
            follow=True
        )

        self.assertRedirects(response, self.url, status_code=302, target_status_code=200)
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.profile_picture))
        self.assertContains(response, 'Default avatar in use.')
        self.assertNotContains(response, 'Remove Picture')

    def test_post_profile_picture_actions_require_login(self):
        existing_picture = self._make_uploaded_image(name='existing.png')
        self.user.profile_picture.save(existing_picture.name, existing_picture, save=True)

        actions = (
            (
                'upload',
                {'profile_picture': self._make_uploaded_image(), 'save_profile_picture': '1'},
            ),
            (
                'remove',
                {'remove_profile_picture': '1'},
            ),
        )

        for action_name, form_input in actions:
            with self.subTest(action=action_name):
                response = self.client.post(self.url, form_input, follow=True)
                self.assertRedirects(
                    response,
                    reverse_next('log_in', self.url),
                    status_code=302,
                    target_status_code=200
                )
                self.assertTemplateUsed(response, 'log_in.html')

        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_picture))

    def test_post_delete_account(self):
        self.client.login(username='exampleuser', password='Password123')
        response = self.client.post(
            self.url,
            {'delete_account': '1', 'confirm_delete': 'on'},
            follow=True
        )
        response_url = reverse('home')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'homepage.html')
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(self._is_logged_in())
