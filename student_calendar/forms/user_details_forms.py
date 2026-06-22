from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError


PROFILE_PICTURE_MAX_SIZE = 2 * 1024 * 1024
ALLOWED_PROFILE_PICTURE_EXTENSIONS = {
    '.jpg': 'jpeg',
    '.jpeg': 'jpeg',
    '.png': 'png',
    '.webp': 'webp',
}


def detect_profile_picture_format(profile_picture):
    """Detect image format from the file header bytes.

    Returns 'jpeg', 'png', 'webp', or None if unrecognised.
    """
    header = profile_picture.read(16)
    profile_picture.seek(0)

    if header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'
    return None


class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'username', 'email']


class ProfilePictureForm(forms.ModelForm):
    profile_picture = forms.FileField(
        required=False,
        widget=forms.FileInput(
            attrs={'accept': '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp'}
        )
    )

    class Meta:
        model = get_user_model()
        fields = ['profile_picture']

    def clean_profile_picture(self):
        """Validate the uploaded profile picture's extension, size, and magic bytes."""
        profile_picture = self.cleaned_data.get('profile_picture')

        if not profile_picture:
            return profile_picture

        extension = Path(profile_picture.name).suffix.lower()
        expected_format = ALLOWED_PROFILE_PICTURE_EXTENSIONS.get(extension)
        if not expected_format:
            raise ValidationError('Upload a JPG, JPEG, PNG, or WEBP image.')

        if profile_picture.size > PROFILE_PICTURE_MAX_SIZE:
            raise ValidationError('Profile picture must be 2 MB or smaller.')

        detected_format = detect_profile_picture_format(profile_picture)
        if detected_format is None:
            raise ValidationError('Upload a valid image file.')

        if detected_format != expected_format:
            raise ValidationError('Upload a JPG, JPEG, PNG, or WEBP image.')

        return profile_picture


class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        old_password_field = self.fields.get('old_password')
        if old_password_field:
            old_password_field.widget.attrs.pop('autofocus', None)


class DeleteAccountForm(forms.Form):
    confirm_delete = forms.BooleanField(
        required=True,
        label='I understand this will permanently delete my account.'
    )
