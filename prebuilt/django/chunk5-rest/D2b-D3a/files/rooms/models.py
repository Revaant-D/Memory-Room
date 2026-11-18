"""The data model: what the app remembers.

Four tables, decided on 16 Nov 2026 (docs/design/2026-11-16-first-draft.md, §6):

    User ──< Place ──< Scan ──< Pin >── Memory >── Place

"──<" reads "has many". A Place is a room. A Scan is one filmed video of it
(and, later, the 3D points built from that video). A Memory is one photo
taken there. A Pin says where one Memory sits inside one Scan, so the same
photo can have a position in every scan of its place.
"""

import math
import os
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from rooms.slugs import unique_slug

# --- Where uploaded files are stored ----------------------------------------
#
# A file is stored under a name the app makes up, inside its place's folder:
#
#     media/places/<place id>/scans/<32 random characters>.mp4
#     media/places/<place id>/scans/<32 random characters>-points.bin
#     media/places/<place id>/memories/<32 random characters>.jpg
#
# The name the phone gave the file never reaches the disk. Only its ending
# (".jpg", ".mp4") is kept, lower-cased, and only if it is short and plain.

_PLAIN_ENDING = re.compile(r"^\.[a-z0-9]{1,5}$")


def _ending(filename):
    ending = os.path.splitext(filename)[1].lower()
    return ending if _PLAIN_ENDING.match(ending) else ""


def scan_video_path(instance, filename):
    return f"places/{instance.place_id}/scans/{uuid.uuid4().hex}{_ending(filename)}"


def scan_points_path(instance, filename):
    return f"places/{instance.place_id}/scans/{uuid.uuid4().hex}-points.bin"


def memory_photo_path(instance, filename):
    return f"places/{instance.place_id}/memories/{uuid.uuid4().hex}{_ending(filename)}"


# --- Place ------------------------------------------------------------------


class Place(models.Model):
    """A room someone wants to keep. Everything else hangs off a place."""

    # settings.AUTH_USER_MODEL is our own User class (accounts/models.py).
    # CASCADE: deleting a user deletes their places.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="places"
    )
    name = models.CharField(max_length=80)
    # The word in the place's address. Made in save(), never typed by a person.
    slug = models.SlugField(max_length=80, editable=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]  # newest first
        constraints = [
            # Two owners may both have "dorm-room"; one owner may not have it twice.
            models.UniqueConstraint(fields=["owner", "slug"], name="unique_slug_per_owner"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Only when the slug is empty, which is only on the first save.
        # A rename keeps the old address, so old links keep working.
        if not self.slug:
            self.slug = unique_slug(self.owner, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """The address of this place's own page, for example /places/dorm-room/."""
        return reverse("place_detail", kwargs={"slug": self.slug})

    def newest_ready_scan(self):
        """The scan the 3D viewer should show: the latest one that finished building.

        Returns None when no scan of this place is ready. No page calls this
        yet; the viewer page will.
        """
        return (
            self.scans.filter(status=Scan.Status.READY).order_by("-taken_on", "-created").first()
        )


# --- Scan -------------------------------------------------------------------


class Scan(models.Model):
    """One filmed video of a place and, once built, the 3D points made from it."""

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"  # the video is here; nothing has run
        BUILDING = "building", "Building"  # the 3D room is being made
        READY = "ready", "Ready"  # points_file holds the room
        FAILED = "failed", "Failed"  # the build did not work

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="scans")
    video = models.FileField(upload_to=scan_video_path)
    # The day the room was filmed. Starts as today; the person can change it.
    taken_on = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UPLOADED)
    # Empty until a build finishes.
    points_file = models.FileField(upload_to=scan_points_path, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_on", "-created"]  # most recently filmed first

    def __str__(self):
        return f"{self.place.name}, filmed {self.taken_on:%d %b %Y}"


# --- Memory -----------------------------------------------------------------


class Memory(models.Model):
    """One photo taken in a place, with an optional caption and date."""

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="memories")
    photo = models.ImageField(upload_to=memory_photo_path)
    caption = models.CharField(max_length=200, blank=True)
    # The day the photo was taken, when known. Empty for a photo with no date.
    taken_on = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "memories"
        # Newest photo first; photos with no date go to the end.
        ordering = [models.F("taken_on").desc(nulls_last=True), "-created"]

    def __str__(self):
        return self.caption or f"Photo {self.pk}"

    def photo_address(self):
        """The address a page uses to show this photo: <img src="...">.

        Photos are private. This is the address of a view that checks the
        owner before handing the file over (views.memory_photo), not a
        direct link to the file. Templates call this instead of building
        the address themselves, so there is one line to change if photos
        ever move (to time-limited bucket links at deployment, say).
        """
        return reverse("memory_photo", kwargs={"pk": self.pk})


# --- Pin --------------------------------------------------------------------


class Pin(models.Model):
    """Where one photo sits inside one scan.

    x, y and z are metres in that scan's own frame: the floor is z = 0 and z
    points up. A position only means something together with its scan, which
    is why the pin belongs to a scan and not to the place.
    """

    class PlacedBy(models.TextChoices):
        USER = "user", "User"  # a person put the pin there
        AI = "ai", "AI"  # the placement model put it there

    memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name="pins")
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="pins")
    x = models.FloatField()
    y = models.FloatField()
    z = models.FloatField()
    placed_by = models.CharField(max_length=4, choices=PlacedBy.choices)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # A photo has at most one position in any one scan.
            models.UniqueConstraint(fields=["memory", "scan"], name="one_pin_per_memory_per_scan"),
        ]

    def __str__(self):
        return f"Pin for memory {self.memory_id} in scan {self.scan_id}"

    def clean(self):
        """The two rules a single field cannot check on its own."""
        errors = []
        # Rule 1: the photo and the scan are of the same place.
        if self.memory_id and self.scan_id and self.memory.place_id != self.scan.place_id:
            errors.append("A pin's photo and scan must belong to the same place.")
        # Rule 2: the position is three real numbers. A failed placement run
        # can produce "not a number" or infinity; neither is a position.
        for value in (self.x, self.y, self.z):
            if value is not None and not math.isfinite(value):
                errors.append("A pin's position must be three real numbers.")
                break
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # full_clean() runs every check: the field rules (placed_by is one of
        # the two words), clean() above, and the one-pin-per-scan rule. Calling
        # it here means the rules hold from every code path (a page, the
        # admin, the shell, an import script), not only from forms.
        self.full_clean()
        super().save(*args, **kwargs)
