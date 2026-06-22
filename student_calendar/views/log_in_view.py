from django.views import View
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from student_calendar.forms import LogInForm
from student_calendar.views.decorators import LogInDisallowedMixin


class LogInView(LogInDisallowedMixin, View):
    """View that handles logging in as a user"""
    http_method_names = ['get', 'post']
    logged_in_redirect_url = settings.LOGGED_IN_REDIRECT_URL

    def get(self, request):
        self.next = request.GET.get('next') or ''
        return self.render()

    def post(self, request):
        form = LogInForm(request.POST)
        self.next = request.POST.get('next') or settings.LOGGED_IN_REDIRECT_URL
        user = form.get_user()
        if user is not None:
            login(request, user)
            return redirect(self.next)
        messages.add_message(request, messages.ERROR, 'Email or Password is invalid.')
        return self.render()

    def render(self):
        form = LogInForm()
        return render(
            self.request,
            'log_in.html',
            {
                'form': form,
                'next': self.next
            })
