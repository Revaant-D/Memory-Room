"""Placing a photo by hand (18 Nov 2026).

The room page sends one request when the person taps the floor where they
stood: POST /scans/<n>/pins/ with the photo's number and the spot's x and y,
in metres in the scan's own frame. The answer is JSON, because the page reads
it and drops the dot in without reloading.
"""

import math

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from rooms.access import get_own_built_scan, get_own_memory
from rooms.models import Pin

# A tap gives a spot on the floor, not a height. The camera is put where a
# phone is usually held: the first real room's cameras were 1.15 to 1.4 m up.
HAND_HEIGHT = 1.4


def pin_json(pin):
    """A pin as the room page reads it."""
    return {
        "memory": pin.memory_id,
        "x": pin.x,
        "y": pin.y,
        "z": pin.z,
        "placedBy": pin.placed_by,
        "camera": pin.camera,
    }


def _error(text):
    return JsonResponse({"error": text}, status=400)


def _number(text):
    """A finite number from the request, or None."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


@login_required
@require_POST
def pin_save(request, pk):
    """Put a photo at the tapped spot in this scan, or move it there.

    Both lookups go through the owner checks, so another person's scan or
    photo is a 404. A photo has one pin per scan: placing it again moves that
    pin, and a moved pin loses any camera direction the AI gave it, since it
    is no longer where that camera stood.
    """
    scan = get_own_built_scan(request.user, pk)
    try:
        memory_id = int(request.POST.get("memory", ""))
    except ValueError:
        return _error("Which photo? The request did not say.")
    memory = get_own_memory(request.user, memory_id)
    if memory.place_id != scan.place_id:
        return _error("That photo belongs to another place.")

    x, y = _number(request.POST.get("x")), _number(request.POST.get("y"))
    if x is None or y is None:
        return _error("The spot must be two numbers.")
    box = scan.room_info.get("box") or {}
    low, high = box.get("low"), box.get("high")
    if low and high and not (low[0] <= x <= high[0] and low[1] <= y <= high[1]):
        return _error("That spot is outside the room.")

    pin, _ = Pin.objects.update_or_create(
        memory=memory,
        scan=scan,
        defaults={"x": x, "y": y, "z": HAND_HEIGHT, "placed_by": Pin.PlacedBy.USER, "camera": None},
    )
    return JsonResponse({"pin": pin_json(pin)})
