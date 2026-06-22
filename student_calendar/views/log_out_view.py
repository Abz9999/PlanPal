from django.contrib.auth import logout
from django.shortcuts import redirect


def log_out(request):
    """View that handles logging out as a user"""
    logout(request)
    return redirect('home')
