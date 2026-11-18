"""Tests for the 3D room page (/scans/<n>/room/) and its points file (/scans/<n>/points.ply)."""

import json
import os

from django.core.files.base import ContentFile
from django.urls import reverse

from rooms.models import Memory, Pin, Place, Scan
from rooms.tests.utils import PASSWORD, TempMediaTestCase, jpeg_file, make_user, video_file

PLY = b"ply\nformat binary_little_endian 1.0\nelement vertex 0\nend_header\n"
BOX = {"low": [0.0, 0.0, 0.0], "high": [4.0, 3.0, 2.5]}


class ScanRoomTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="First flat")
        self.scan = self.ready_scan()
        self.client.login(username="ana", password=PASSWORD)

    def ready_scan(self, made_up=False):
        scan = Scan.objects.create(place=self.place, video=video_file())
        scan.points_file.save("points.ply", ContentFile(PLY), save=False)
        scan.status = Scan.Status.READY
        scan.room_info = {"n_points": 0, "box": BOX, "made_up": made_up}
        scan.save()
        return scan

    def page(self, scan=None):
        return reverse("scan_room", kwargs={"pk": (scan or self.scan).pk})

    def points(self, scan=None):
        return reverse("scan_points", kwargs={"pk": (scan or self.scan).pk})

    def page_data(self, response):
        """The JSON the page hands to the viewer (Django's json_script)."""
        html = response.content.decode()
        start = html.index('<script id="room-data" type="application/json">') + len(
            '<script id="room-data" type="application/json">'
        )
        return json.loads(html[start: html.index("</script>", start)])

    # --- who can see it ---

    def test_page_and_points_need_login(self):
        self.client.logout()
        for address in (self.page(), self.points()):
            response = self.client.get(address)
            self.assertEqual(response.status_code, 302, address)
            self.assertTrue(response["Location"].startswith(reverse("login")), address)

    def test_other_user_gets_404(self):
        self.client.logout()
        self.client.login(username="ben", password=PASSWORD)
        self.assertEqual(self.client.get(self.page()).status_code, 404)
        self.assertEqual(self.client.get(self.points()).status_code, 404)

    # --- the page ---

    def test_page_shows_the_viewer(self):
        response = self.client.get(self.page())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="room"')
        self.assertContains(response, "viewer/roomviewer.js")
        data = self.page_data(response)
        self.assertTrue(data["points"].startswith(self.points() + "?v="), data["points"])
        self.assertEqual(data["box"], BOX)
        self.assertEqual(data["pins"], [])

    def test_points_address_changes_when_the_room_is_replaced(self):
        # Review, 18 Nov: the browser keeps the points for an hour. Importing a real
        # room over a made-up one must not leave the made-up points on screen.
        before = self.page_data(self.client.get(self.page()))["points"]
        self.scan.points_file.save("points.ply", ContentFile(PLY), save=True)
        after = self.page_data(self.client.get(self.page()))["points"]
        self.assertNotEqual(before, after)
        self.assertTrue(after.startswith(self.points()))

    def test_scan_not_built_gives_404(self):
        scan = Scan.objects.create(place=self.place, video=video_file())
        self.assertEqual(self.client.get(self.page(scan)).status_code, 404)
        self.assertEqual(self.client.get(self.points(scan)).status_code, 404)

    def test_made_up_room_says_so(self):
        response = self.client.get(self.page(self.ready_scan(made_up=True)))
        self.assertContains(response, "MADE-UP ROOM")

    def test_real_room_has_no_made_up_notice(self):
        self.assertNotContains(self.client.get(self.page()), "MADE-UP ROOM")

    def test_pins_reach_the_page(self):
        memory = Memory.objects.create(place=self.place, photo=jpeg_file(), caption="Move-in day")
        Pin.objects.create(memory=memory, scan=self.scan, x=1.0, y=2.0, z=1.5, placed_by="ai")
        pins = self.page_data(self.client.get(self.page()))["pins"]
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0]["label"], "Move-in day")
        self.assertEqual((pins[0]["x"], pins[0]["y"], pins[0]["z"]), (1.0, 2.0, 1.5))
        self.assertEqual(pins[0]["placedBy"], "ai")
        self.assertEqual(pins[0]["photo"], memory.photo_address())
        self.assertEqual(pins[0]["page"], reverse("memory_edit", kwargs={"pk": memory.pk}))

    def test_pins_of_another_scan_left_out(self):
        other = self.ready_scan()
        memory = Memory.objects.create(place=self.place, photo=jpeg_file())
        Pin.objects.create(memory=memory, scan=other, x=1.0, y=1.0, z=1.0, placed_by="user")
        self.assertEqual(self.page_data(self.client.get(self.page()))["pins"], [])

    def test_caption_cannot_break_out_of_the_data(self):
        memory = Memory.objects.create(place=self.place, photo=jpeg_file(), caption="</script><b>hi")
        Pin.objects.create(memory=memory, scan=self.scan, x=1.0, y=1.0, z=1.0, placed_by="user")
        response = self.client.get(self.page())
        self.assertNotContains(response, "</script><b>hi")
        self.assertEqual(self.page_data(response)["pins"][0]["label"], "</script><b>hi")

    # --- the points file ---

    def test_points_served_to_owner(self):
        response = self.client.get(self.points())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertEqual(response["Cache-Control"], "private, max-age=3600")
        self.assertEqual(b"".join(response.streaming_content), PLY)

    def test_points_file_missing_gives_404(self):
        os.remove(self.scan.points_file.path)
        self.assertEqual(self.client.get(self.points()).status_code, 404)

    # --- the place page ---

    def test_place_page_labels_a_made_up_room(self):
        # Review, 18 Nov: only the 3D page said so; the place page looked the same.
        self.ready_scan(made_up=True)
        self.assertContains(self.client.get(self.place.get_absolute_url()), "MADE-UP ROOM")

    def test_place_page_does_not_label_a_real_room(self):
        self.assertNotContains(self.client.get(self.place.get_absolute_url()), "MADE-UP")

    def test_place_page_links_only_ready_scans(self):
        waiting = Scan.objects.create(place=self.place, video=video_file())
        response = self.client.get(self.place.get_absolute_url())
        self.assertContains(response, self.page())
        self.assertNotContains(response, self.page(waiting))
        self.assertContains(response, "View the room in 3D")
