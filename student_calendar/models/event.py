# Created by: Frankie Cole
# A simple model for an arbitray calander event TEMPLATE
# version: 3.0

from datetime import datetime
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from student_calendar.models import Category, User

class Event(models.Model):

    # ===============
    # Variables
    # ===============
    # When event is imported, these variables are avaliable to use. They will mainly be used in querying e.g. [e for e in events if e.days_mask & MON]
    MON = 1 << 0 # 0000001
    TUE = 1 << 1 # 0000010
    WED = 1 << 2 # 0000100
    THU = 1 << 3 # 0001000
    FRI = 1 << 4 # 0010000
    SAT = 1 << 5 # 0100000
    SUN = 1 << 6 # 1000000

    # Map that links my variables to a string that can be displayed
    DAY_MAP = [
    (MON, "Mon"),
    (TUE, "Tue"),
    (WED, "Wed"),
    (THU, "Thu"),
    (FRI, "Fri"),
    (SAT, "Sat"),
    (SUN, "Sun"),
    ]

    # ===============
    # Choice Classes
    # ===============

    class Priority(models.IntegerChoices):
        CRITICAL = 5, "Critical"
        HIGH = 4, "High"
        MEDIUM = 3, "Medium"
        LOW = 2, "Low"
        VERY_LOW = 1, "Very Low"


    # ===============
    # Model fields
    # ===============

    title = models.CharField(max_length=50, blank=False, null=False)

    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)

    number_of_days = models.IntegerField(blank=False, null=False, default=1)

    # Optional Fields
    max_instances = models.IntegerField(null=True, blank=True, default=0)
    repeat_days = models.IntegerField(blank=True, null=False, default=0)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True) # Add a max_length later

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="events") # PROTECT ensures a category field cannot be deleted if its being used

    importance = models.IntegerField(choices=Priority.choices, default=Priority.VERY_LOW)
    duration = models.IntegerField(blank=True, null=True)
    repeat_weeks = models.IntegerField(default=1)

    # For the system
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # khan - added max_instances
    # Stores the total number of instances pre-created for this event template.
    # Calculated as: count_of_repeat_days * repeat_weeks when the event is created.
    # Used to derive counters and track placement progress across ScheduleEvent rows.
    max_instances = models.IntegerField(null=True, blank=True, default=0)

    # ===============
    # Meta Options
    # ===============

    class Meta:
        ordering = ['start'] # orders events by start time


    # ===============
    # Functions
    # ===============

    # function that ensures data is formatted correctly

    def clean(self):
        super().clean()
        errors = {}
        self._validate_start_end(errors)
        self._validate_duration(errors)
        self._validate_repeat(errors)
        self._validate_importance(errors)
        if errors:
            raise ValidationError(errors)

    def _validate_start_end(self, errors):
        if self.start and not self.end and not self.duration:
            errors["start"] = "Start requires either an end time or a duration."
        if self.end and not self.start:
            errors["end"] = "End time requires a start time."
        if self.start and self.end and self.end <= self.start:
            errors["end"] = "End time must be after start time."

    def _validate_duration(self, errors):
        if errors:
            return
        if self.start and self.end:
            self.duration = max(1, int((self.end - self.start).total_seconds() // 60))
            return
        if self.start or self.end:
            return
        if not self.duration:
            errors["duration"] = "Duration is required if start/end are not provided."
        elif self.duration <= 0:
            errors["duration"] = "Duration must be a positive number."

    def _validate_repeat(self, errors):
        if self.repeat_weeks is not None and self.repeat_weeks <= 0:
            errors["repeat_weeks"] = "Repeat weeks must be at least 1."
        if self.number_of_days < 1 or self.number_of_days > 7:
            errors["number_of_days"] = "Number of days must be between 1 and 7."
        if self.repeat_days and bin(self.repeat_days).count("1") != self.number_of_days:
            errors["repeat_days"] = f"You selected {bin(self.repeat_days).count('1')} days but number_of_days is {self.number_of_days}."
        max_mask = self.MON | self.TUE | self.WED | self.THU | self.FRI | self.SAT | self.SUN
        if self.repeat_days < 0 or self.repeat_days > max_mask:
            errors["repeat_days"] = "Invalid repeat days bitmask."

    def _validate_importance(self, errors):
        valid_priorities = [choice.value for choice in self.Priority]
        if self.importance not in valid_priorities:
            errors["importance"] = "Invalid importance value."

    # ==================
    # HELPER FUNCTIONS
    # ==================

    # returns a list of the repeat days respective strings
    def get_repeat_days(self):
        return [name for bit, name in self.DAY_MAP if self.repeat_days & bit]

    # returns a single string containg all the repeat days
    def get_repeat_days_display(self):
        return ", ".join(self.get_repeat_days())

    # String overide. (What is displayed when printing an event)
    def __str__(self):
        return f"{self.title}: {self.start} - {self.end}, {self.repeat_days}"

    # - Khan
    # fixed duration display - old code showed "0 minutes" for 60 min events
    # now properly handles hours and minutes separately

    # updated duration_format to also work out duration from start/end times
    # so fixed events dont just say "fixed time" - they show the actual length
    def duration_format(self):
        dur = self.duration
        if not dur and self.start and self.end:
            dur = max(1, int((self.end - self.start).total_seconds() / 60))
        if not dur:
            return "no duration set"
        hours = dur // 60
        minutes = dur % 60
        if hours > 0 and minutes > 0:
            return f"{hours} {'hr' if hours == 1 else 'hrs'} {minutes} mins"
        elif hours > 0:
            return f"{hours} {'hr' if hours == 1 else 'hrs'}"
        else:
            return f"{minutes} mins"


    def scheduled_occurrences(self, schedule_events):
        return schedule_events.filter(event=self).count()

    def next_occurrence(self, schedule_events):
        this_schedule_events = schedule_events.filter(event__pk=self.pk)

        next_scheduled_time = timezone.make_aware(datetime.max)
        for schedule_event in this_schedule_events:
            if schedule_event.placed_start < next_scheduled_time:
                next_scheduled_time = schedule_event.placed_start

        return next_scheduled_time
