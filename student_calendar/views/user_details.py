from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from student_calendar.forms import (
    DeleteAccountForm,
    ProfilePictureForm,
    UserDetailsForm,
    UserPasswordChangeForm,
)


def default_forms(request):
    # all four forms in their default state
    return {
        'user_form': UserDetailsForm(instance=request.user),
        'profile_picture_form': ProfilePictureForm(instance=request.user),
        'delete_form': DeleteAccountForm(),
        'password_form': UserPasswordChangeForm(user=request.user),
    }


def handle_delete_account(request):
    # delete the account if the confirmation checkbox is ticked
    delete_form = DeleteAccountForm(request.POST)
    if delete_form.is_valid():
        request.user.delete()
        logout(request)
        return redirect('home'), {}
    return None, {'delete_form': delete_form}


def handle_remove_profile_picture(request):
    # remove the current profile picture and clear it from the database
    if request.user.profile_picture:
        request.user.profile_picture.delete(save=False)
        request.user.profile_picture = None
        request.user.save(update_fields=['profile_picture'])
    return redirect('user_details'), {}


def handle_save_profile_picture(request):
    # upload and save a new profile picture
    profile_picture_form = ProfilePictureForm(
        request.POST, request.FILES, instance=request.user
    )
    if profile_picture_form.is_valid():
        profile_picture_form.save()
        return redirect('user_details'), {}
    return None, {'profile_picture_form': profile_picture_form}


def handle_save_details(request):
    # save changes to the user's name, username, and email
    user_form = UserDetailsForm(request.POST, instance=request.user)
    if user_form.is_valid():
        user_form.save()
        return redirect('user_details'), {}
    return None, {'user_form': user_form}


def handle_change_password(request):
    # change the user's password and keep them logged in
    password_form = UserPasswordChangeForm(user=request.user, data=request.POST)
    if password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password updated successfully.', extra_tags='password-change-toast')
        return redirect('user_details'), {}
    return None, {'password_form': password_form}


POST_HANDLERS = {
    'delete_account': handle_delete_account,
    'remove_profile_picture': handle_remove_profile_picture,
    'save_profile_picture': handle_save_profile_picture,
    'save_details': handle_save_details,
    'change_password': handle_change_password,
}


def handle_post(request, forms):
    # send the POST to the right handler based on which button was clicked
    for action, handler in POST_HANDLERS.items():
        if action in request.POST:
            response, overrides = handler(request)
            forms.update(overrides)
            return response
    return None


@login_required(login_url='log_in')
def user_details(request):
    """Handle viewing, updating, and deleting the authenticated user's account."""
    forms = default_forms(request)

    if request.method == 'POST':
        response = handle_post(request, forms)
        if response:
            return response

    return render(request, 'user_details.html', forms)
