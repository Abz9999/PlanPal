from django.urls import reverse
from with_asserts.mixin import AssertHTMLMixin


def reverse_next(name, next):
    return_url = reverse(name)
    return_url += f'?next={next}'
    return return_url


class LogInTester:
    def _is_logged_in(self):
        return '_auth_user_id' in self.client.session.keys()


class MenuTesterMixin(AssertHTMLMixin):
    menu_urls = [
        reverse('log_out'),
    ]

    def assert_menu(self, response):
        for url in self.menu_urls:
            with self.assertHTML(response, f'a[href="{url}"]'):
                pass

    def assert_not_menu(self, response):
        for url in self.menu_urls:
            self.assertNotHTML(response, f'a[href="{url}"]')
