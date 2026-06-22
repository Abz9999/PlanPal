from django.apps import AppConfig


class StudentCalendarConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'student_calendar'

    def ready(self):
        import student_calendar.signals.default_categories_signal