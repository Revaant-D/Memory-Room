"""The landing room: a thinned, public copy of one built room (18 Nov 2026).

The builder chose to show their own room on the logged-out front page, with
no photos. Only the points become public: never a photo, a caption or a
name. The copy lives at media/landing/room.ply, and the landing_points view
hands it to anyone. `manage.py landing_room <scan>` makes it;
`manage.py landing_room --remove` takes it down.
"""

import math
from pathlib import Path

from django.conf import settings

from rooms.roomfolder import BYTES_PER_POINT

LANDING_FILE = "landing/room.ply"
END = b"end_header\n"


def landing_path():
    return Path(settings.MEDIA_ROOT) / LANDING_FILE


def landing_exists():
    return landing_path().is_file()


def write_landing(scan, max_points=150_000):
    """Write every n-th point of this scan's room, at most max_points. Returns the count.

    The scan's file was checked when it was imported (import_room), so its
    layout is Memory Room's own: a short header, then 15 bytes a point.
    """
    with scan.points_file.open("rb") as source:
        data = source.read()
    end = data.index(END) + len(END)
    count = int(data[:end].decode("ascii").split("element vertex ")[1].split()[0])
    body = memoryview(data)[end:]
    step = max(1, math.ceil(count / max_points))
    kept = range(0, count, step)
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        f"element vertex {len(kept)}\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property uchar red\nproperty uchar green\nproperty uchar blue\n"
        "end_header\n"
    ).encode("ascii")
    path = landing_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as out:
        out.write(header)
        for i in kept:
            out.write(body[i * BYTES_PER_POINT:(i + 1) * BYTES_PER_POINT])
    return len(kept)


def remove_landing():
    landing_path().unlink(missing_ok=True)
