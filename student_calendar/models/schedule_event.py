# Created by Theodore Tsiberopoulos
# Modified by Khan
# schedule_event.py

from django.db import models
from student_calendar.models import Schedule, Event, User
from django.core.exceptions import ValidationError

class ScheduleEvent(models.Model):
    """Model used to represent the relation between a schedule and an event"""
    class Status(models.IntegerChoices):
        CREATED = 1,    #created
        SCHEDULED = 2,  #scheduled
        COMPLETED = 3,  #completed
        MISSED = 4,     #missed      

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, blank=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False)
    placed_start = models.DateTimeField(blank=True, null=True)
    placed_end = models.DateTimeField(blank=True, null=True)
    status = models.IntegerField(choices=Status.choices, blank=False, default=Status.CREATED)   # need choices
    placed_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    # Immutable integer identifying this specific instance within its parent event template.
    # Scoped per template — gym gets 1-9, uni gets 1-12, independently.
    # Assigned at event creation and never changes, even as status changes.
    # Allows stable reference to "gym instance 3" regardless of what happens to it.
    occurrence_index = models.IntegerField(null=True, blank=True)


    def clean(self):
        super().clean()

        if self.placed_start and self.placed_end and self.placed_start > self.placed_end:
            raise ValidationError({self.placed_end: 'Placed end time must be after placed start time'})
        
        