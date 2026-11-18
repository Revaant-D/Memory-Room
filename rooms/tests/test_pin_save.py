"""Tests for placing a photo by hand: POST /scans/<n>/pins/ (18 Nov)."""

from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse

from rooms.models import Memory, Pin, Place, Scan
from rooms.tests.utils import PASSWORD, TempMediaTestCase, jpeg_file, make_user, video_file

PLY = b"ply\nformat binary_little_endian 1.0\nelement vertex 0\nend_header\n"
BOX = {"low": [-1.0, -2.0, 0.0], "high": [3.0, 2.0, 2.5]}
TURNED = {"rotation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "vfov": 60.0}


class PinSaveTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="First flat")
        self.scan = self.ready_scan(self.place)
        self.memory = Memory.objects.create(place=self.place, photo=jpeg_file())
        self.client.login(username="ana", password=PASSWORD)

    def ready_scan(self, place, ready=True):
        scan = Scan.objects.create(place=place, video=video_file())
        if ready:
            scan.points_file.save("points.ply", ContentFile(PLY), save=False)
            scan.status = Scan.Status.READY
            scan.room_info = {"n_points": 0, "box": BOX, "made_up": False}
            scan.save()
        return scan

    def url(self, scan=None):
        return reverse("pin_save", kwargs={"pk": (scan or self.scan).pk})

    def post(self, scan=None, **data):
        values = {"memory": self.memory.pk, "x": "1.25", "y": "-0.5"}
        values.update(data)
        return self.client.post(self.url(scan), values)

    def test_needs_login(self):
        self.client.logout()
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("login")))
        self.assertEqual(Pin.objects.count(), 0)

    def test_get_refused(self):
        self.assertEqual(self.client.get(self.url()).status_code, 405)

    def test_places_a_photo(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"pin": {"memory": self.memory.pk, "x": 1.25, "y": -0.5, "z": 1.4, "placedBy": "user", "camera": None}},
        )
        pin = Pin.objects.get()
        self.assertEqual((pin.memory, pin.scan), (self.memory, self.scan))
        self.assertEqual((pin.x, pin.y, pin.z, pin.placed_by, pin.camera), (1.25, -0.5, 1.4, "user", None))

    def test_moves_an_existing_pin_and_clears_its_camera(self):
        Pin.objects.create(memory=self.memory, scan=self.scan, x=0.0, y=0.0, z=1.2, placed_by="ai", camera=TURNED)
        self.assertEqual(self.post(x="2", y="1").status_code, 200)
        pin = Pin.objects.get()
        self.assertEqual((pin.x, pin.y, pin.z, pin.placed_by, pin.camera), (2.0, 1.0, 1.4, "user", None))

    def test_other_users_scan_404(self):
        bens_place = Place.objects.create(owner=self.ben, name="Ben's")
        self.assertEqual(self.post(scan=self.ready_scan(bens_place)).status_code, 404)
        self.assertEqual(Pin.objects.count(), 0)

    def test_other_users_photo_404(self):
        bens_place = Place.objects.create(owner=self.ben, name="Ben's")
        bens_photo = Memory.objects.create(place=bens_place, photo=jpeg_file())
        self.assertEqual(self.post(memory=bens_photo.pk).status_code, 404)
        self.assertEqual(Pin.objects.count(), 0)

    def test_photo_of_another_place_400(self):
        other_place = Place.objects.create(owner=self.ana, name="Second flat")
        photo = Memory.objects.create(place=other_place, photo=jpeg_file())
        response = self.post(memory=photo.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(Pin.objects.count(), 0)

    def test_scan_not_ready_404(self):
        self.assertEqual(self.post(scan=self.ready_scan(self.place, ready=False)).status_code, 404)

    def test_not_numbers_400(self):
        for bad in ("abc", "nan", "inf", ""):
            with self.subTest(x=bad):
                response = self.post(x=bad)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())
        self.assertEqual(Pin.objects.count(), 0)

    def test_memory_not_a_number_400(self):
        self.assertEqual(self.post(memory="first").status_code, 400)

    def test_outside_the_box_400(self):
        for x, y in (("-1.01", "0"), ("0", "2.01")):
            with self.subTest(x=x, y=y):
                self.assertEqual(self.post(x=x, y=y).status_code, 400)
        self.assertEqual(Pin.objects.count(), 0)

    def test_csrf_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="ana", password=PASSWORD)
        response = strict.post(self.url(), {"memory": self.memory.pk, "x": "1", "y": "0"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Pin.objects.count(), 0)
