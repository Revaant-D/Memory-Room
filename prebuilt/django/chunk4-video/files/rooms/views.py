"""The pages of the rooms app. One function per page.

Every page below the home page needs a logged-in user (@login_required sends
anyone else to the login page) and gets its place through rooms/access.py,
which answers 404 for a place that is not this user's.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from rooms.access import get_own_place, get_own_scan
from rooms.forms import PlaceForm, ScanForm
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
    context = {
        "place": place,
        "scans": place.scans.all(),  # most recently filmed first (Scan.Meta.ordering)
    }
    return render(request, "rooms/place_detail.html", context)


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


# --- Room scans -------------------------------------------------------------


@login_required
def scan_create(request, slug):
    """Show the "add a room video" form, or save the uploaded video."""
    place = get_own_place(request.user, slug)
    if request.method == "POST":
        # request.FILES holds the upload. Django has already written a large
        # file to a temporary file on disk while it arrived.
        form = ScanForm(request.POST, request.FILES)
        if form.is_valid():  # runs rooms/validators.py on the video
            form.instance.place = place  # from the address, never from the form
            form.save()  # the file moves into media/places/<id>/scans/ here
            messages.success(request, "Room video added.")
            return redirect(place)
    else:
        form = ScanForm()
    return render(request, "rooms/scan_form.html", {"form": form, "place": place})


@login_required
def scan_delete(request, pk):
    """Ask first (GET), then delete the scan and its files (POST)."""
    scan = get_own_scan(request.user, pk)
    place = scan.place
    if request.method == "POST":
        scan.delete()  # rooms/signals.py removes the video from disk
        messages.success(request, "Room video deleted.")
        return redirect(place)
    return render(request, "rooms/scan_confirm_delete.html", {"scan": scan, "place": place})
