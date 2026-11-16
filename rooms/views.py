"""The pages of the rooms app. One function per page."""

from django.shortcuts import render


def home(request):
    """The front page: says what Memory Room is."""
    return render(request, "rooms/home.html")
