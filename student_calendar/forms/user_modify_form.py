from django import forms
from django.contrib.auth import authenticate
from django.core.validators import MinLengthValidator
from student_calendar.models import User


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']


class NewPasswordMixin(forms.Form):
    """
    Mixin for adding password and confirm password field.
    """
    new_password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(),
        validators=[
            MinLengthValidator(
                limit_value=8,
                message='Password must be at least eight characters long'
            )
        ]
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput()
    )

    def clean(self):
        super().clean()
        new_password = self.cleaned_data.get('new_password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if new_password != confirm_password:
            self.add_error(
                'confirm_password',
                'Passwords do not match.'
            )

class SignUpForm(NewPasswordMixin, forms.ModelForm):
    """
    Form that allows users to create a new user object
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']

    def save(self):
        super().save(commit=False)
        user = User.objects.create_user(
            self.cleaned_data.get('username'),
            first_name=self.cleaned_data.get('first_name'),
            last_name=self.cleaned_data.get('last_name'),
            email=self.cleaned_data.get('email'),
            password=self.cleaned_data.get('new_password')
        )
        return user
