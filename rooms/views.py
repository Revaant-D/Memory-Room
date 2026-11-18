"""The pages of the rooms app. One function per page.

Every page below the home page needs a logged-in user (@login_required sends
anyone else to the login page) and gets its place through rooms/access.py,
which answers 404 for a place that is not this user's.
"""

import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from rooms.access import get_own_memory, get_own_place, get_own_scan
from rooms.forms import MemoryForm, MemoryUploadForm, PlaceForm, ScanForm
from rooms.models import Memory, Place, Scan
from rooms.photos import photo_taken_on

# The only types a photo file is ever served as (see memory_photo).
PHOTO_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


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


def _get_own_built_scan(user, pk):
    """This user's scan, if its 3D room has been built; otherwise 404."""
    scan = get_own_scan(user, pk)
    if scan.status != Scan.Status.READY or not scan.points_file:
        raise Http404("This room has not been built yet.")
    return scan


@login_required
def scan_room(request, pk):
    """The 3D room built from one scan, with its placed photos as dots.

    The page itself is light: the room's points are fetched by the browser
    from scan_points below, and drawn by static/viewer/roomviewer.js.
    """
    scan = _get_own_built_scan(request.user, pk)
    pins = [
        {
            "id": pin.pk,
            "x": pin.x,
            "y": pin.y,
            "z": pin.z,
            "placedBy": pin.placed_by,
            "label": pin.memory.caption or "Photo with no caption",
            "photo": pin.memory.photo_address(),
            "page": reverse("memory_edit", kwargs={"pk": pin.memory_id}),
        }
        for pin in scan.pins.select_related("memory").order_by("pk")
    ]
    # Handed to the page's script as JSON (json_script in the template), so a
    # caption can never be read as code.
    # The file's own random name is added to the address, so the address changes
    # whenever a room is imported again, and a browser never draws an older
    # room (a made-up one, say) from its cache. The view ignores it.
    version = os.path.basename(scan.points_file.name).split("-")[0]
    room_data = {
        "points": reverse("scan_points", kwargs={"pk": scan.pk}) + f"?v={version}",
        "box": scan.room_info.get("box"),
        "pins": pins,
    }
    n_points = scan.room_info.get("n_points")
    return render(request, "rooms/scan_room.html", {
        "scan": scan,
        "place": scan.place,
        "made_up": scan.room_info.get("made_up") is True,
        "points_text": f"{n_points:,} points" if isinstance(n_points, int) else "",
        "room_data": room_data,
    })


@login_required
def scan_points(request, pk):
    """Hand over a built room's points file (PLY), to its owner only.

    Like memory_photo: nothing serves media/ directly, so the file is only
    reachable through this owner check.
    """
    scan = _get_own_built_scan(request.user, pk)
    try:
        file = open(scan.points_file.path, "rb")
    except (FileNotFoundError, ValueError):
        raise Http404("This room's points file is missing.")
    response = FileResponse(file, content_type="application/octet-stream")
    response["Cache-Control"] = "private, max-age=3600"
    return response


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
                    taken_on = photo_taken_on(photo)  # None when the photo has no date
                    if taken_on and taken_on > timezone.localdate():
                        # A camera clock set ahead. The edit page refuses future
                        # dates, so keep none rather than one that can't be saved back.
                        taken_on = None
                    Memory.objects.create(place=place, photo=photo, taken_on=taken_on)
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
    # The type comes from a short list, never guessed from the stored name, so a
    # file can only ever be shown as a picture or offered as a download.
    ending = os.path.splitext(memory.photo.name)[1].lower()
    kind = PHOTO_TYPES.get(ending, "application/octet-stream")
    response = FileResponse(file, content_type=kind)  # sends the file in pieces and closes it afterwards
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
