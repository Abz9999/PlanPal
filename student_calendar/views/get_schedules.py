# Created by Frankie
# GET    — returns all the user's schedules as JSON
# POST   — creates a new schedule and links it to the user
# DELETE /api/schedules/<id>/ — deletes a schedule owned by the user

import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from student_calendar.models.schedule import Schedule
from student_calendar.models.user_schedule import UserSchedule

@login_required
@require_http_methods(["GET", "POST"])
def get_schedules(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            title = body.get("title", "").strip()
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"error": "Invalid JSON."}, status=400)

        if not title:
            return JsonResponse({"error": "Title is required."}, status=400)

        duplicate = UserSchedule.objects.filter(
            user=request.user, schedule__title__iexact=title
        ).exists()
        if duplicate:
            return JsonResponse({"error": "You already have a schedule with that name."}, status=400)

        schedule = Schedule.objects.create(title=title, is_active=False)
        UserSchedule.objects.create(user=request.user, schedule=schedule)
        return JsonResponse({"id": schedule.id, "title": schedule.title, "is_active": schedule.is_active}, status=201)

    # GET
    user_schedules = UserSchedule.objects.filter(user=request.user).select_related('schedule')
    data = [
        {'id': us.schedule.id, 'title': us.schedule.title, 'is_active': us.schedule.is_active}
        for us in user_schedules
    ]
    return JsonResponse({'schedules': data})


@login_required
@require_http_methods(["DELETE"])
def delete_schedule(request, schedule_id):
    link = get_object_or_404(UserSchedule, user=request.user, schedule__id=schedule_id)
    schedule = link.schedule
    schedule.delete()  # cascades to UserSchedule and ScheduleEvent
    return JsonResponse({"ok": True})
