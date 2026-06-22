from django.shortcuts import redirect
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def login_disallowed(function):
    """
    Decorator that prevents a view from being accessed while logged in
    """
    def modified_function(request):
        if request.user.is_authenticated:
            return redirect(settings.LOGGED_IN_REDIRECT_URL)
        else:
            return function(request)
    return modified_function


class LogInDisallowedMixin:
    """
    Mixin which prevents logged in users from accessing some class-based views
    """
    logged_in_redirect_url = None

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return self.redirect_when_logged_in()
        return super().dispatch(*args, **kwargs)

    def redirect_when_logged_in(self):
        url = self.get_log_in_redirect_url()
        return redirect(url)

    def get_log_in_redirect_url(self):
        if self.logged_in_redirect_url is None:
            raise ImproperlyConfigured(
                "Log-in redirect url has not been configured correctly"
            )
        else:
            return self.logged_in_redirect_url
