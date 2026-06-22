from django.shortcuts import render
from student_calendar.views.decorators import login_disallowed


@login_disallowed
def home(request):
    """Return the website's log in/sign up page"""

    return render(request, 'homepage.html')
