# python
from django.contrib import admin
from .models import *

# Event
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "start", "end", "duration", "days", "repeat_weeks", "location", "description", "category", "importance", "max_instances"]
    list_filter = ["start"]
    search_fields = ["title", "start", "end", "category__name"]

    def days(self, obj):
        return obj.get_repeat_days_display()

# User
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "first_name", "last_name", "email"]
    list_filter = ["username", "first_name", "last_name", "email"]
    search_fields = ["username", "first_name", "last_name", "email"]

# User Schedule
@admin.register(UserSchedule)
class UserScheduleAdmin(admin.ModelAdmin):
    list_display = ["user", "schedule"]
    list_filter = ["user", "schedule"]
    search_fields = ["user", "schedule"]

# Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "colour"]
    list_filter = ["name", "colour"]
    search_fields = ["name", "colour"]

# Schedule
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ["title"]
    list_filter = ["title"]
    search_fields = ["title"]

# Schedule Event
@admin.register(ScheduleEvent)
class ScheduleEventAdmin(admin.ModelAdmin):
    list_display = ["id","schedule", "event", "placed_start", "placed_end", "status", "placed_by","occurrence_index"]
    list_filter = ["schedule", "event", "placed_start", "placed_end", "status", "placed_by"]
    search_fields = ["schedule", "event", "placed_start", "placed_end", "status", "placed_by"]
