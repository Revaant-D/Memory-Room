"""The pages of the rooms app. One function per page.

Every page below the home page needs a logged-in user (@login_required sends
anyone else to the login page) and gets its place through rooms/access.py,
which answers 404 for a place that is not this user's.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from rooms.access import get_own_place
from rooms.forms import PlaceForm
from rooms.models import Place


def home(request):
    """The front page. A logged-in person goes straight to their places."""
    if request.user.is_authenticated:
        return redirect("place_list")
    return render(request, "rooms/home.html")


# --- Places -----------------------------------------------------------------


@login_required
def place_list(request):
    """Every place that belongs to the logged-in user, newest first."""
    places = Place.objects.filter(owner=request.user)
    return render(request, "rooms/place_list.html", {"places": places})


@login_required
def place_create(request):
    """Show the "new place" form, or save it."""
    if request.method == "POST":
        form = PlaceForm(request.POST)
        if form.is_valid():
            # The owner comes from the session, never from the form.
            form.instance.owner = request.user
            place = form.save()  # Place.save() makes the slug here
            messages.success(request, "Place created.")
            return redirect(place)  # goes to place.get_absolute_url()
    else:
        form = PlaceForm()
    return render(request, "rooms/place_form.html", {"form": form})


@login_required
def place_detail(request, slug):
    """One place: its room scans and its photos."""
    place = get_own_place(request.user, slug)
    return render(request, "rooms/place_detail.html", {"place": place})


@login_required
def place_edit(request, slug):
    """Rename a place. Its address does not change."""
    place = get_own_place(request.user, slug)
    if request.method == "POST":
        form = PlaceForm(request.POST, instance=place)
        if form.is_valid():
            form.save()
            messages.success(request, "Place renamed.")
            return redirect(place)
    else:
        form = PlaceForm(instance=place)
    return render(request, "rooms/place_form.html", {"form": form, "place": place})


@login_required
def place_delete(request, slug):
    """Ask first (GET), then delete the place and everything in it (POST)."""
    place = get_own_place(request.user, slug)
    if request.method == "POST":
        # Deleting the place deletes its scans, photos and pins with it
        # (on_delete=CASCADE in models.py); rooms/signals.py removes the files.
        place.delete()
        messages.success(request, "Place deleted.")
        return redirect("place_list")
    context = {
        "place": place,
        "scan_count": place.scans.count(),
        "memory_count": place.memories.count(),
    }
    return render(request, "rooms/place_confirm_delete.html", context)
