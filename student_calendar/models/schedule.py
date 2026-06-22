# Created by Theodore Tsiberopoulos
from django.db import models

class Schedule(models.Model):
    """Model used to represent a schedule"""

    title = models.CharField(max_length=100, blank=False)
    is_active = models.BooleanField(default=False)
