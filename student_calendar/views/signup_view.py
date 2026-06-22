from django.conf import settings
from django.contrib.auth import login
from django.views.generic.edit import FormView
from django.urls import reverse
from student_calendar.forms import SignUpForm
from student_calendar.views.decorators import LogInDisallowedMixin

class SignupView(LogInDisallowedMixin, FormView):
    form_class = SignUpForm
    template_name = 'signup.html'
    logged_in_redirect_url = settings.LOGGED_IN_REDIRECT_URL

    def form_valid(self, form):
        self.object = form.save()
        login(self.request, self.object)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(settings.LOGGED_IN_REDIRECT_URL)
