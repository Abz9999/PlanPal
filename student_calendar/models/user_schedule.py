# Created by Theodore Tsiberopoulos
from django.db import models
from student_calendar.models import User, Schedule

class UserSchedule(models.Model):
    """Model used to represent the relation between a user and a schedule"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
