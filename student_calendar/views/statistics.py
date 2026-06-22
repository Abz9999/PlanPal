# Created by Khan

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json
from student_calendar import statistics_service


@login_required
def statistics(request):
    period = statistics_service.normalise_period(request.GET.get("period", "all"))
    start_date, end_date = statistics_service.resolve_period(period)
    categories = statistics_service.get_category_breakdown(
        request.user,
        start_date,
        end_date,
    )
    trends = statistics_service.get_weekly_trends(request.user)

    context = {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "hero": statistics_service.get_hero_stats(request.user),
        "categories": categories,
        "categories_json": json.dumps(_build_category_chart_data(categories)),
        "heatmap": statistics_service.get_weekly_heatmap(
            request.user,
            start_date,
            end_date,
        ),
        "streaks": statistics_service.get_streak_leaderboard(request.user),
        "trends": trends,
        "trends_json": json.dumps(trends),
    }
    return render(request, "statistics.html", context)


def _build_category_chart_data(categories):
    return [
        {
            "name": category["name"],
            "colour": category["colour"],
            "hours": category["hours"],
        }
        for category in categories
    ]