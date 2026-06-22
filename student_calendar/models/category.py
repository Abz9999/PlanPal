# Created by Frankie Cole
# This is a model to store event category types and their respeective card colour

from django.db import models
from django.core.validators import RegexValidator

# This Regex ensures a HEX value for a colour
hex_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a valid HEX color code."
)


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    colour = models.CharField(max_length=7, validators=[hex_validator])

    def __str__(self):
        return self.name

