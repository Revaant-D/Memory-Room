"""manage.py landing_room <scan> | --remove

Makes the public copy of one built room for the logged-out front page, or
takes it down. Refuses a room that is not built, and a made-up one (every
page showing a made-up room must say so, and the front page would not).
"""

from django.core.management.base import BaseCommand, CommandError

from rooms.landing import remove_landing, write_landing
from rooms.models import Scan


class Command(BaseCommand):
    help = "Put a thinned, public copy of one built room on the front page (no photos), or --remove it."

    def add_arguments(self, parser):
        parser.add_argument("scan_id", type=int, nargs="?", help="the scan's number (the admin site lists them)")
        parser.add_argument("--max-points", type=int, default=150_000, help="at most this many points (150,000)")
        parser.add_argument("--remove", action="store_true", help="take the front-page room down")

    def handle(self, scan_id=None, max_points=150_000, remove=False, **options):
        if remove:
            remove_landing()
            self.stdout.write("The front page has no room now.")
            return
        if scan_id is None:
            raise CommandError("Which scan? Give its number, or --remove.")
        scan = Scan.objects.filter(pk=scan_id).first()
        if scan is None:
            raise CommandError(f"No scan number {scan_id}.")
        if scan.status != Scan.Status.READY or not scan.points_file:
            raise CommandError(f"Scan {scan_id}'s room is not built, so there is nothing to show.")
        if scan.room_info.get("made_up") is True:
            raise CommandError(f"Scan {scan_id} is a MADE-UP ROOM (a stand-in, not a reconstruction); "
                               f"the front page will not show it.")
        kept = write_landing(scan, max_points=max_points)
        self.stdout.write(f"The front page now shows scan {scan_id}: {kept:,} points, no photos.")
