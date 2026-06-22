# Created by Frankie.
# This is a signal that checks when a user is created, when one is it will add the default categories to the model.

from django.db.models.signals import post_save
from django.dispatch import receiver
from student_calendar.models import Category, User

DEFAULT_CATEGORIES = [
    ("Other", "#7D7B7B"),
    ("Hobbies", "#3788d8"),
    ("Extra Curricular", "#dc3545"),
    ("Education", "#ffc107"),
    ("Independent Study", "#38F527"),
    ("Self-Care", "#9F27F5"),
    ("Work", "#F527DD"),
]

@receiver(post_save, sender=User)
def create_default_categories(sender, instance, created, **kwargs):
    if created:
        for name, colour in DEFAULT_CATEGORIES:
            Category.objects.get_or_create(name=name, colour=colour)
