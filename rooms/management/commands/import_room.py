"""manage.py import_room <scan number> <room folder or .zip> [--made-up]

Brings a room built by the Colab notebook into the app: checks it
(rooms/roomfolder.py), stores its points.ply as the scan's points file, keeps
the room's facts in Scan.room_info, and marks the scan ready. The 3D viewer
page then shows it.

For the first draft this is how a built room reaches Django (the builder's
decision, 17 Nov 2026). By 8 Dec a Django view starts the GPU job itself, and
its result goes through the same checks.
"""

import shutil
import tempfile
import zipfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from rooms.models import Scan
from rooms.roomfolder import POINTS_FILE, RoomError, check_room, open_room


class Command(BaseCommand):
    help = "Attach a room built by the Colab notebook to a scan, and mark the scan ready."

    def add_arguments(self, parser):
        parser.add_argument("scan_id", type=int, help="the scan's number (the admin site lists them)")
        parser.add_argument("room", help="the room folder, or the .zip the notebook made")
        parser.add_argument(
            "--made-up",
            action="store_true",
            help="allow a room made by the stand-in model; every page will label it MADE-UP ROOM",
        )

    def handle(self, scan_id, room, made_up, **options):
        try:
            scan = Scan.objects.get(pk=scan_id)
        except Scan.DoesNotExist:
            raise CommandError(f"No scan number {scan_id}. The admin site lists scans with their numbers.")

        points = tempfile.TemporaryFile()  # removed when closed
        try:
            with open_room(Path(room)) as found:
                info = check_room(found, made_up_allowed=made_up)
                with found.open(POINTS_FILE) as source:
                    # Read it all once, here: a damaged zip shows itself now,
                    # before anything is written into media/.
                    shutil.copyfileobj(source, points)
        except RoomError as problem:
            points.close()
            raise CommandError(str(problem)) from problem
        except (zipfile.BadZipFile, OSError) as problem:
            points.close()
            raise CommandError(f"The room's files could not be read; the zip or folder may be damaged "
                               f"({problem}). Download it again.") from problem

        old = scan.points_file.name if scan.points_file else None
        with points:
            points.seek(0)
            # Copied into media/, under a new random name ending "-points.ply".
            scan.points_file.save(POINTS_FILE, File(points, name=POINTS_FILE), save=False)

        info["imported"] = timezone.now().isoformat(timespec="seconds")
        scan.room_info = info
        scan.status = Scan.Status.READY
        try:
            scan.save(update_fields=["points_file", "room_info", "status"])
        except Exception:
            scan.points_file.storage.delete(scan.points_file.name)  # don't leave an orphan file
            raise
        if old:
            scan.points_file.storage.delete(old)  # a room imported again replaces the old one

        if info["made_up"]:
            self.stdout.write("MADE-UP ROOM (stand-in model, not a reconstruction). Pages will say so.")
        self.stdout.write(f"Scan {scan.pk} is ready: {info['n_points']:,} points{_box_text(info['box'])}.")


def _box_text(box):
    """", in a box 4.12 x 3.05 m across and 2.48 m high", or "" if the box is missing."""
    try:
        size = [high - low for low, high in zip(box["low"], box["high"])]
        return f", in a box {size[0]:.2f} x {size[1]:.2f} m across and {size[2]:.2f} m high"
    except (KeyError, TypeError, ValueError, IndexError):
        return ""
