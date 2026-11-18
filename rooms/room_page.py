"""What the room page needs from the database (18 Nov 2026, the Dollhouse look).

The place page shows its newest built room this way, and /scans/<n>/room/
shows any one built room the same way. Everything the page's script needs
goes into one dict, handed over with json_script, so a caption can never be
read as code.
"""

import os

from django.urls import reverse

from rooms.pins import pin_json


def _photo_id(value):
    """The ?photo= value as a number, or None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def points_url(scan):
    """The address of a built scan's points (owner only).

    The file's own random name goes into the address, so a re-imported room
    is never drawn from the browser's cache (review, 18 Nov).
    """
    version = os.path.basename(scan.points_file.name).split("-")[0]
    return reverse("scan_points", kwargs={"pk": scan.pk}) + f"?v={version}"


def room_context(scan, open_id=None):
    """The template context for the room page of this built scan.

    open_id is the ?photo= value from the address. It opens that photo only
    if it is one of this place's photos; anything else opens the room as usual.
    """
    place = scan.place
    pins = {pin.memory_id: pin for pin in scan.pins.all()}
    photos = [
        {
            "id": memory.pk,
            "caption": memory.caption,
            "date": f"{memory.taken_on:%d %b %Y}".lstrip("0") if memory.taken_on else "",
            "src": memory.photo_address(),
            "edit": reverse("memory_edit", kwargs={"pk": memory.pk}),
            "pin": pin_json(pins[memory.pk]) if memory.pk in pins else None,
        }
        for memory in place.memories.all()  # newest first, undated last (Memory.Meta)
    ]
    wanted = _photo_id(open_id)
    made_up = scan.room_info.get("made_up") is True
    return {
        "scan": scan,
        "place": place,
        "made_up": made_up,
        "scans": place.scans.all(),
        "room_data": {
            "points": points_url(scan),
            "box": scan.room_info.get("box"),
            "madeUp": made_up,
            "pinUrl": reverse("pin_save", kwargs={"pk": scan.pk}),
            "photos": photos,
            "open": wanted if any(photo["id"] == wanted for photo in photos) else None,
        },
    }
