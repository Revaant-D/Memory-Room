"""The pages of the rooms app. One function per page.

Every page below the home page needs a logged-in user (@login_required sends
anyone else to the login page) and gets its place through rooms/access.py,
which answers 404 for a place that is not this user's.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from rooms.access import get_own_memory, get_own_place, get_own_scan
from rooms.forms import MemoryForm, MemoryUploadForm, PlaceForm, ScanForm
from rooms.models import Memory, Place
from rooms.photos import photo_taken_on


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
        "memories": place.memories.all(),  # newest photo first, undated last
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


# --- Photos (memories) ------------------------------------------------------


@login_required
def memory_create(request, slug):
    """Show the "add photos" form, or save the uploaded photos."""
    place = get_own_place(request.user, slug)
    if request.method == "POST":
        form = MemoryUploadForm(request.POST, request.FILES)
        if form.is_valid():  # every file has passed rooms/validators.py by here
            photos = form.cleaned_data["photos"]
            # atomic: either every photo gets its row, or none does.
            with transaction.atomic():
                for photo in photos:
                    Memory.objects.create(
                        place=place,
                        photo=photo,
                        taken_on=photo_taken_on(photo),  # None when the photo has no date
                    )
            count = len(photos)
            messages.success(request, f"{count} photo{'' if count == 1 else 's'} added.")
            return redirect(place)
    else:
        form = MemoryUploadForm()
    return render(request, "rooms/memory_upload.html", {"form": form, "place": place})


@login_required
def memory_photo(request, pk):
    """Hand over one photo file, to its owner only.

    Nothing serves the media/ folder directly. Every <img> on the site points
    here, so a photo's address is useless to anyone who is not logged in as
    its owner: they get the login page or a 404.
    """
    memory = get_own_memory(request.user, pk)
    try:
        file = open(memory.photo.path, "rb")
    except (FileNotFoundError, ValueError):
        # The row exists but its file is gone (media/ was cleared, say).
        raise Http404("This photo's file is missing.")
    response = FileResponse(file)  # sends the file in pieces and closes it afterwards
    # The owner's browser may keep its copy for an hour; shared caches may not keep one.
    response["Cache-Control"] = "private, max-age=3600"
    return response


@login_required
def memory_edit(request, pk):
    """Change a photo's caption and date."""
    memory = get_own_memory(request.user, pk)
    place = memory.place
    if request.method == "POST":
        form = MemoryForm(request.POST, instance=memory)
        if form.is_valid():
            form.save()
            messages.success(request, "Photo updated.")
            return redirect(place)
    else:
        form = MemoryForm(instance=memory)
    context = {"form": form, "memory": memory, "place": place}
    return render(request, "rooms/memory_form.html", context)


@login_required
def memory_delete(request, pk):
    """Ask first (GET), then delete the photo and its file (POST)."""
    memory = get_own_memory(request.user, pk)
    place = memory.place
    if request.method == "POST":
        memory.delete()  # rooms/signals.py removes the file from disk
        messages.success(request, "Photo deleted.")
        return redirect(place)
    context = {"memory": memory, "place": place}
    return render(request, "rooms/memory_confirm_delete.html", context)
