from django import forms
from datetime import datetime, timedelta, date as date_cls, timezone as dt_timezone
from student_calendar.models import Event, Category
from django.core.exceptions import ValidationError

SENTINEL_DATE = date_cls(1970, 1, 1)

DAYS = [
    (1, "MON"),
    (2, "TUE"),
    (4, "WED"),
    (8, "THU"),
    (16, "FRI"),
    (32, "SAT"),
    (64, "SUN"),
]


class LenientDateField(forms.DateField):
    """DateField that returns None instead of raising on bad input."""

    def to_python(self, value):
        try:
            return super().to_python(value)
        except forms.ValidationError:
            return None


class LenientTimeField(forms.TimeField):
    """TimeField that returns None instead of raising on bad input."""

    def to_python(self, value):
        try:
            return super().to_python(value)
        except forms.ValidationError:
            return None


def clean_date_v2(cleaned):
    """Populate cleaned['start'] and cleaned['end'] from one of 5 valid input cases."""
    start_date = cleaned.get("start_date")
    start_time = cleaned.get("start_time")
    end_date = cleaned.get("end_date")
    end_time = cleaned.get("end_time")
    duration = cleaned.get("duration")

    # Case 1: full start + end — this is a one-off pinned to a specific datetime,
    # so it can't also "repeat" across days/weeks. Normalise both repeat fields
    # to 1 so the user doesn't have to redo anything if they accidentally set them.
    if start_date and start_time and end_date and end_time:
        cleaned["start"] = datetime.combine(start_date, start_time)
        cleaned["end"] = datetime.combine(end_date, end_time)
        cleaned["number_of_days"] = 1
        cleaned["repeat_days"] = 0
        cleaned["repeat_weeks"] = 1
        return


    # Case 2: start date+time, no end
    if start_date and start_time and not end_date and not end_time:
        if not duration:
            raise ValidationError("Duration is required when no end time is specified.")
        start = datetime.combine(start_date, start_time)
        cleaned["start"] = start
        cleaned["end"] = start + timedelta(minutes=duration)
        return

    # Case 4: start date only (no time) — flexible time, end left null
    if start_date and not start_time and not end_date and not end_time:
        if not duration:
            raise ValidationError("Duration is required when only a date is specified.")
        from datetime import time as time_cls
        cleaned["start"] = datetime.combine(start_date, time_cls(0, 0, 0))
        cleaned["end"] = None
        return

    # Case 5: start+end time only — stored as explicit UTC on sentinel date
    if not start_date and start_time and not end_date and end_time:
        if end_time <= start_time:
            raise ValidationError("End time must be after start time.")
        cleaned["start"] = datetime(1970, 1, 1, start_time.hour, start_time.minute, 0,
                                    tzinfo=dt_timezone.utc)
        cleaned["end"] = datetime(1970, 1, 1, end_time.hour, end_time.minute, 0,
                                  tzinfo=dt_timezone.utc)
        return

    # Case 3: no dates at all
    if not start_date and not start_time and not end_date and not end_time:
        if not duration:
            raise ValidationError(
                "You must either provide both start and end dates OR provide a duration."
            )
        return

    # Partial / invalid combination — reject rather than silently clear
    if start_date and not start_time:
        raise ValidationError("Please provide a start time with the start date, or remove the date.")
    if end_date and not end_time:
        raise ValidationError("Please provide an end time with the end date.")
    if end_time and not start_time and not start_date:
        raise ValidationError("Please provide a start time or start date.")
    if start_time and not start_date and end_date:
        raise ValidationError("Please provide a start date to match the end date, or remove all dates.")
    raise ValidationError(
        "Invalid date combination. Please provide valid start/end dates and times, "
        "or leave all date fields empty."
    )


def clean_days(cleaned):
    """Convert selected day checkbox values into a single bitmask integer."""
    selected_days = cleaned.get("repeat_days")
    if selected_days:
        cleaned["repeat_days"] = sum(int(day) for day in selected_days)
    else:
        cleaned["repeat_days"] = 0


def clean_duration(cleaned):
    """Populate cleaned['duration'] from date/time fields or from hours/minutes."""
    start_date = cleaned.get("start_date")
    start_time = cleaned.get("start_time")
    end_date = cleaned.get("end_date")
    end_time = cleaned.get("end_time")

    # Case 1: duration = end - start
    if start_date and start_time and end_date and end_time:
        start = datetime.combine(start_date, start_time)
        end = datetime.combine(end_date, end_time)
        cleaned["duration"] = max(1, int((end - start).total_seconds() / 60))
        return

    # Case 5: duration from time difference on a neutral date
    if not start_date and start_time and not end_date and end_time:
        neutral = date_cls(2000, 6, 15)
        diff = datetime.combine(neutral, end_time) - datetime.combine(neutral, start_time)
        if diff.total_seconds() > 0:
            cleaned["duration"] = max(1, int(diff.total_seconds() / 60))
        return

    # Cases 2, 3, 4: use explicit hours/minutes
    h = cleaned.get("hours") or 0
    m = cleaned.get("minutes") or 0
    if h != 0 or m != 0:
        cleaned["duration"] = h * 60 + m


class CreateEvent(forms.ModelForm):
    """Multi-step form for creating or editing an Event template."""

    repeat_days = forms.MultipleChoiceField(
        choices=DAYS,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "horizontal-checkboxes"}),
        required=False,
    )

    start = forms.DateTimeField(widget=forms.HiddenInput(), required=False)
    end = forms.DateTimeField(widget=forms.HiddenInput(), required=False)

    start_date = LenientDateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    start_time = LenientTimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    end_date = LenientDateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_time = LenientTimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))

    duration = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    hours = forms.IntegerField(
        min_value=0, max_value=23, required=False,
        widget=forms.NumberInput(attrs={"class": "duration-input", "placeholder": "hrs"}),
    )
    minutes = forms.IntegerField(
        min_value=0, max_value=59, required=False,
        widget=forms.NumberInput(attrs={"class": "duration-input", "placeholder": "mins"}),
    )

    class Meta:
        model = Event
        fields = [
            "title", "start", "end", "duration", "location",
            "number_of_days", "repeat_days", "repeat_weeks",
            "description", "category", "importance",
        ]
        widgets = {
            "repeat_weeks": forms.NumberInput(attrs={"class": "small-input", "min": 1, "max": 10, "value": 1}),
            "number_of_days": forms.NumberInput(attrs={"class": "small-input", "min": 1, "max": 7, "value": 1}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["category"].queryset = Category.objects.all()
            self.fields["repeat_weeks"].initial = 1
            self.fields["number_of_days"].initial = 1

    def clean(self):
        cleaned = super().clean()
        clean_days(cleaned)
        self.instance.repeat_days = cleaned.get("repeat_days", 0)
        clean_duration(cleaned)
        clean_date_v2(cleaned)
        return cleaned
