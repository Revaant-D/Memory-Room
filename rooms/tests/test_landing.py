"""Tests for the landing room: a thinned, public copy of one built room (18 Nov).

The builder chose to show their own room, with no photos, on the logged-out
front page. Only points go public: no photos, captions or names.
"""

import struct

from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.urls import reverse

from rooms.landing import landing_exists, remove_landing
from rooms.models import Place, Scan
from rooms.tests.utils import PASSWORD, TempMediaTestCase, make_user, video_file

BOX = {"low": [0.0, 0.0, 0.0], "high": [4.0, 3.0, 2.5]}


def ply(points):
    """A PLY in the layout Memory Room writes: x y z floats, then r g b bytes, per point."""
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        f"element vertex {len(points)}\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property uchar red\nproperty uchar green\nproperty uchar blue\n"
        "end_header\n"
    ).encode("ascii")
    return header + b"".join(struct.pack("<fffBBB", *p) for p in points)


def read_ply(data):
    end = data.index(b"end_header\n") + len(b"end_header\n")
    count = int(data[:end].decode().split("element vertex ")[1].split()[0])
    body = data[end:]
    assert len(body) == count * 15, "body length"
    return [struct.unpack_from("<fffBBB", body, i * 15) for i in range(count)]


POINTS = [(float(i), float(i) / 2, 1.0, i, 255 - i, 7) for i in range(10)]


class LandingRoomTests(TempMediaTestCase):
    def setUp(self):
        self.place = Place.objects.create(owner=make_user("ana"), name="Octave Room")
        self.scan = self.built_scan()
        # The class shares one temporary media folder: leave no landing room behind.
        self.addCleanup(remove_landing)

    def built_scan(self, made_up=False, ready=True):
        scan = Scan.objects.create(place=self.place, video=video_file())
        if ready:
            scan.points_file.save("points.ply", ContentFile(ply(POINTS)), save=False)
            scan.status = Scan.Status.READY
            scan.room_info = {"n_points": len(POINTS), "box": BOX, "made_up": made_up}
            scan.save()
        return scan

    def run_command(self, *args):
        call_command("landing_room", *[str(a) for a in args], stdout=None)

    def served(self):
        response = self.client.get(reverse("landing_points"))
        return response, (b"".join(response.streaming_content) if response.status_code == 200 else b"")

    def test_command_writes_a_thinned_copy(self):
        self.run_command(self.scan.pk, "--max-points", 4)
        response, data = self.served()
        kept = read_ply(data)
        self.assertLessEqual(len(kept), 4)
        self.assertGreater(len(kept), 0)
        for point in kept:
            self.assertIn(point, POINTS)

    def test_command_refuses_made_up_room(self):
        with self.assertRaises(CommandError) as caught:
            self.run_command(self.built_scan(made_up=True).pk)
        self.assertIn("MADE-UP", str(caught.exception))
        self.assertFalse(landing_exists())

    def test_command_refuses_scan_not_ready(self):
        with self.assertRaises(CommandError):
            self.run_command(self.built_scan(ready=False).pk)
        self.assertFalse(landing_exists())

    def test_remove_takes_it_down(self):
        self.run_command(self.scan.pk)
        self.assertTrue(landing_exists())
        call_command("landing_room", "--remove", stdout=None)
        self.assertFalse(landing_exists())
        self.assertEqual(self.served()[0].status_code, 404)

    def test_file_is_public(self):
        self.run_command(self.scan.pk)
        response, data = self.served()  # nobody is logged in
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "public, max-age=3600")
        self.assertEqual(sorted(read_ply(data)), sorted(POINTS))  # 10 points: under the cap, all kept

    def test_404_when_absent(self):
        self.assertEqual(self.served()[0].status_code, 404)

    def test_home_mentions_the_room_only_when_it_exists(self):
        self.assertNotContains(self.client.get(reverse("home")), reverse("landing_points"))
        self.run_command(self.scan.pk)
        self.assertContains(self.client.get(reverse("home")), reverse("landing_points"))

    def test_logged_in_home_still_goes_to_places(self):
        self.run_command(self.scan.pk)
        self.client.login(username="ana", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("home")), reverse("place_list"))
