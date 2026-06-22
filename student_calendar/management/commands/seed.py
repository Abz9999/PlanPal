import random
from django.core.management.base import BaseCommand, CommandError
from student_calendar.models import *
import urllib.request
import ssl
from datetime import timedelta
from django.utils import timezone
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from student_calendar.views.create_event import build_schedule_instances

# Disable SSL certificate verification for development/seeding
ssl._create_default_https_context = ssl._create_unverified_context


user_fixtures = [
    {'username': 'johndoe', 'email': 'john.doe@example.org', 'first_name': 'John', 'last_name': 'Doe'},
    {'username': 'janedoe', 'email': 'jane.doe@example.org', 'first_name': 'Jane', 'last_name': 'Doe'},
    {'username': 'charlie', 'email': 'charlie.johnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson'},
    {'username': 'BobRoss', 'email': 'Bob.Rossn@example.org', 'first_name': 'Bob', 'last_name': 'Ross'},
    {'username': 'AdaLoveLace', 'email': 'Ada.LoveLace@example.org', 'first_name': 'Ada', 'last_name': 'LoveLace'},
]

category_fixtures = {
     'Work': ["Meeting", "Project deadline", "Shift"],
     'Self-Care':["Spa day", "Hair appointment", "Nails appointment"],
     'Independent Study': ["Study", "Work on assignment", "Group meeting"],
     'Education': ["SGT Class", "Lecture", "Assignment deadline"],
     'Extra Curricular': ["Science club", "Hackathon", "AI workshop"],
     'Hobbies': ["Tennis", "Art", "Pottery", "Play guitar"],
     'Other': ["Wedding", "Concert", "Homeless Volunteering"]
}


class Command(BaseCommand):
    """
    Build automation command to seed the database with data.

    This command inserts a small set of known users (``user_fixtures``).
    Each generated user receives the same default password.

    It then repeatedly generates random events until ``EVENT_COUNT`` total events
    exist in the database.

    Attributes:
        EVENT_COUNT (int): Target total number of events in the database.
        WEEKS (int): Maximum number of weeks of events to seed the database with.
        DEFAULT_PASSWORD (str): Default password assigned to all created users.
        help (str): Short description shown in ``manage.py help``.
        faker (Faker): Locale-specific Faker instance used for random data.
    """
    EVENT_COUNT = 50
    WEEKS = 10

    DEFAULT_PASSWORD = 'Password123'
    help = 'Seeds the database with sample data'

    def __init__(self, *args, **kwargs):
        """Initialize the command with a locale-specific Faker instance."""
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        """
        Django entrypoint for the command.

        Runs the full seeding workflow and stores ``self.users``, ``self.events`` and ``self.schedule_events``
        for any post-processing or debugging (not required for operation).
        """

        self.create_admin_user()
        self.create_users()
        self.users = User.objects.all()
        self.categories = Category.objects.all()
        self.create_events()
        self.events = Event.objects.all()
        self.create_schedule()
        self.create_schedule_events()
        self.schedule_events = ScheduleEvent.objects.all()


    #ADMIN

    def create_admin_user(self):
        """Create superuser for admin panel access."""
        try:
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@gmail.com',
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                print('✓ Superuser created: admin / admin123')
            else:
                print('✓ Superuser already exists: admin')
        except Exception as e:
            print(f'! Failed to create superuser: {e}')

    #USERS

    def create_users(self):
        """
        Create fixture users.

        The process is idempotent in spirit: attempts that fail (e.g., due to
        uniqueness constraints on username/email) are ignored and generation continues.
        """
        self.generate_user_fixtures()

    def generate_user_fixtures(self):
        """Attempt to create each predefined fixture user."""
        for data in user_fixtures:
            self.try_create_user(data)

    def try_create_user(self, data):
        """
        Attempt to create a user and ignore any errors.

        Args:
            data (dict): Mapping with keys ``username``, ``email``,
                ``first_name``, and ``last_name``.
        """
        try:
            self.create_user(data)
        except IntegrityError:
            pass  # Duplicate username or email, skip

    def create_user(self, data):
        """
        Create a user with the default password.

        Args:
            data (dict): Mapping with keys ``username``, ``email``,
                ``first_name``, and ``last_name``.
        """
        User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=Command.DEFAULT_PASSWORD,
            first_name=data['first_name'],
            last_name=data['last_name'],
        )


    #EVENTS

    def create_events(self):
        """
        Create random events up to EVENT_COUNT.

        The process is idempotent in spirit: attempts that fail (e.g., due to
        uniqueness constraints on username/email) are ignored and generation continues.
        """
        self.generate_random_events()

    def generate_random_events(self):
        """
        Generate random events until the database contains EVENT_COUNT events.

        Prints a simple progress indicator to stdout during generation.
        """
        event_count = Event.objects.count()
        while  event_count < self.EVENT_COUNT:
            print(f"Seeding event {event_count}/{self.EVENT_COUNT}", end='\r')
            self.generate_event()
            event_count = Event.objects.count()
        print("Event seeding complete.      ")

    def generate_event(self):
        """
        Generate a single random event and attempt to insert it.
        """
        user = random.choice(self.users)
        category = random.choice(self.categories)
        title = random.choice(category_fixtures[category.name]) #!
        duration = 15*random.randint(1, 8)
        start = random.choice([None, random_date(week_start(), week_start() + timedelta(weeks=self.WEEKS))])
        end = None
        if start != None:
            end = start + timedelta(minutes=duration)

        number_of_days = random.choice([1, 1, 2, random.randint(1, 7)])
        repeat_days = random_repeat_days(start, number_of_days)
        repeat_weeks = random.choice([1, 1, 1, random.randint(1, 10)])
        max_instances = number_of_days * repeat_weeks

        importance = random.choice(Event.Priority.choices)[0]
        location = f'Location {category.id}'
        description = f'{Event.Priority.choices[5-importance][1]} priority, {category.name} at {location}'

        self.try_create_event({'user': user, 'title': title, 'duration': duration, 'start': start,
        'end': end, 'number_of_days': number_of_days, 'repeat_weeks': repeat_weeks, 'repeat_days': repeat_days,
        'category': category, 'importance': importance, 'location': location, 'description': description,
        'max_instances': max_instances})

    def try_create_event(self, data):
        """
        Attempt to create a event and ignore any errors.

        Args:
            data (dict): Mapping with keys ``title``, ``duration``, ``start``, ``end``, ``number_of_days``,
            ``repeat_days``, ``repeat_weeks``, ``category``, ``importance``, ``location``, ``description``
            and ``max_instances``.
        """
        try:
            self.create_event(data)
        except (IntegrityError, ValidationError):
            pass  # Random data failed validation or caused duplicate, skip

    def create_event(self, data):
        """
        Create a event.

        Args:
            data (dict): Mapping with keys ``title``, ``duration``, ``start``, ``end``, ``number_of_days``,
            ``repeat_days``, ``repeat_weeks``, ``category``, ``importance``, ``location``, ``description``
            and ``max_instances``.
        """
        Event.objects.create(
            user=data['user'],
            title=data['title'],
            duration=data['duration'],
            start=data['start'],
            end=data['end'],
            number_of_days=data['number_of_days'],
            repeat_days=data['repeat_days'],
            repeat_weeks=data['repeat_weeks'],
            max_instances=data['max_instances'],
            category=data['category'],
            importance=data['importance'],
            location=data['location'],
            description=data['description'],
        )

    #SCHEDULE

    def create_schedule(self):
        """
        Create a schedule.
        """
        for user in self.users:
            sched = Schedule.objects.get_or_create(title=f"{user.username}'s Schedule", is_active=True)[0]
            UserSchedule.objects.create(user=user,schedule=sched)
        print("Schedule seeding complete.      ")


        #SCHEDULED_EVENTS

    def create_schedule_events(self):

        self.generate_schedule_events()
        print("ScheduleEvent seeding complete.      ")

    def generate_schedule_events(self):
        """
        Generate ScheduleEvents for every event instance with fixed dates

        Prints a simple progress indicator to stdout during generation.
        """
        sched_events = self.events
        se_count = 0
        for event in sched_events:
            print(f"Seeding scheduled events {se_count}/{self.EVENT_COUNT}", end='\r')
            self.generate_schedule_event(event)
            se_count += 1

    def generate_schedule_event(self, event):
        """
        Generate all schedule_events for a single event, and attempt to insert it.
        """

        user_schedule = UserSchedule.objects.filter(user=event.user)[0]
        user = event.user
        weeks_count = event.repeat_weeks

        instances = build_schedule_instances(event, user_schedule, user, weeks_count)
        ScheduleEvent.objects.bulk_create(instances)


#HELPERS

def random_date(start, end):
    diff = end - start
    diff_in_second = (diff.days*24*60*60)
    random_second = random.randrange(diff_in_second)

    return start + timedelta(seconds=random_second)

def getDayIndex(dayIndex):
    if dayIndex == 0:
        dayIndex = 6
    else:
        dayIndex -= 1

    return dayIndex

def week_start():
    today = timezone.now()
    """Adjusting index to start on Mon = 0"""
    diff = int(today.strftime("%w"))
    diff = getDayIndex(diff)

    monday = today - timedelta(days=diff)
    return monday

def random_repeat_days(start, number_of_days):
    """Indices of possible days"""
    possible_days = [0,1,2,3,4,5,6]
    repeat_days_list = []
    if start != None:
        dayIndex = getDayIndex(int(start.strftime("%w")))
        repeat_days_list.append(pow(2, dayIndex))
        possible_days.remove(dayIndex)
        number_of_days -= 1

    for i in range(number_of_days):
        rand_day = random.choice(possible_days)
        repeat_days_list.append(pow(2, rand_day))
        possible_days.remove(rand_day)
        number_of_days -= 1

    return sum(repeat_days_list)
