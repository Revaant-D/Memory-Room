"""Tests for the data model: Place, Scan, Memory, Pin and their rules."""

import datetime
import os

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from rooms.models import Memory, Pin, Place, Scan
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user, video_file

# --- Place and its address word ---------------------------------------------


class PlaceTests(TestCase):
    def setUp(self):
        self.ana = make_user("ana")

    def make_place(self, name, owner=None):
        return Place.objects.create(owner=owner or self.ana, name=name)

    def test_slug_made_from_name(self):
        self.assertEqual(self.make_place("Dorm Room 214").slug, "dorm-room-214")

    def test_same_name_same_owner_numbered(self):
        slugs = [self.make_place("Dorm Room").slug for _ in range(3)]
        self.assertEqual(slugs, ["dorm-room", "dorm-room-2", "dorm-room-3"])

    def test_same_name_two_owners(self):
        ben = make_user("ben")
        self.assertEqual(self.make_place("Dorm Room").slug, "dorm-room")
        self.assertEqual(self.make_place("Dorm Room", owner=ben).slug, "dorm-room")

    def test_reserved_word(self):
        # /places/new/ is the "create a place" page, so no place may live there.
        self.assertEqual(self.make_place("New").slug, "new-2")

    def test_name_without_letters(self):
        self.assertEqual(self.make_place("🏠🏠").slug, "place")
        self.assertEqual(self.make_place("🏠🏠").slug, "place-2")

    def test_long_name(self):
        name = ("abcdefghi " * 8).strip()  # 79 characters; the cut lands on a hyphen
        self.assertEqual(len(name), 79)
        slug = self.make_place(name).slug
        self.assertLessEqual(len(slug), 70)
        self.assertFalse(slug.endswith("-"))
        # A second place with the same long name still fits the 80-character column.
        second = self.make_place(name)
        second.full_clean()
        self.assertEqual(second.slug, slug + "-2")

    def test_slug_kept_on_rename(self):
        place = self.make_place("Dorm Room")
        place.name = "Old Dorm"
        place.save()
        place.refresh_from_db()
        self.assertEqual(place.name, "Old Dorm")
        self.assertEqual(place.slug, "dorm-room")

    def test_str_is_name(self):
        self.assertEqual(str(self.make_place("Dorm Room")), "Dorm Room")


# --- Scan, Memory and their files -------------------------------------------


class ModelTestCase(TempMediaTestCase):
    """Shared set-up: one user and one place, plus short ways to make rows."""

    def setUp(self):
        self.ana = make_user("ana")
        self.place = Place.objects.create(owner=self.ana, name="Dorm Room")

    def make_scan(self, place=None, **fields):
        fields.setdefault("video", video_file())
        return Scan.objects.create(place=place or self.place, **fields)

    def make_memory(self, place=None, **fields):
        fields.setdefault("photo", jpeg_file())
        return Memory.objects.create(place=place or self.place, **fields)


class ScanTests(ModelTestCase):
    def test_scan_defaults(self):
        scan = self.make_scan()
        scan.refresh_from_db()
        self.assertEqual(scan.status, "uploaded")
        self.assertEqual(scan.status, Scan.Status.UPLOADED)
        self.assertEqual(scan.taken_on, timezone.localdate())
        self.assertFalse(scan.points_file)

    def test_newest_ready_scan(self):
        day = datetime.date
        self.make_scan(taken_on=day(2026, 9, 1), status=Scan.Status.READY)
        wanted = self.make_scan(taken_on=day(2026, 11, 1), status=Scan.Status.READY)
        self.make_scan(taken_on=day(2026, 11, 10), status=Scan.Status.UPLOADED)
        self.make_scan(taken_on=day(2026, 11, 12), status=Scan.Status.FAILED)
        self.assertEqual(self.place.newest_ready_scan(), wanted)

    def test_newest_ready_scan_none(self):
        self.make_scan()
        self.assertIsNone(self.place.newest_ready_scan())


class MemoryTests(ModelTestCase):
    def test_memory_optional_fields(self):
        memory = Memory(place=self.place, photo=jpeg_file(), caption="", taken_on=None)
        memory.full_clean()  # raises if either empty value were refused

    def test_memory_order(self):
        day = datetime.date
        march = self.make_memory(taken_on=day(2026, 3, 1))
        undated = self.make_memory(taken_on=None)
        may = self.make_memory(taken_on=day(2026, 5, 9))
        self.assertEqual(list(self.place.memories.all()), [may, march, undated])


class FileTests(ModelTestCase):
    def test_stored_name_is_generated(self):
        memory = self.make_memory(photo=jpeg_file("../../my room 🏠.JPG"))
        self.assertRegex(memory.photo.name, r"^places/\d+/memories/[0-9a-f]{32}\.jpg$")

    def test_video_stored_name(self):
        scan = self.make_scan(video=video_file("Room Video.MP4"))
        self.assertRegex(scan.video.name, r"^places/\d+/scans/[0-9a-f]{32}\.mp4$")

    def test_long_file_name(self):
        memory = self.make_memory(photo=jpeg_file("a" * 196 + ".jpg"))
        self.assertTrue(os.path.exists(memory.photo.path))

    def test_delete_memory_removes_file(self):
        memory = self.make_memory()
        path = memory.photo.path
        self.assertTrue(os.path.exists(path))
        memory.delete()
        self.assertFalse(os.path.exists(path))

    def test_delete_scan_removes_files(self):
        scan = self.make_scan(points_file=SimpleUploadedFile("points.bin", b"points"))
        self.assertRegex(scan.points_file.name, r"^places/\d+/scans/[0-9a-f]{32}-points\.bin$")
        paths = [scan.video.path, scan.points_file.path]
        self.assertTrue(all(os.path.exists(p) for p in paths))
        scan.delete()
        self.assertFalse(any(os.path.exists(p) for p in paths))

    def test_delete_place_removes_rows_and_files(self):
        scan = self.make_scan()
        first = self.make_memory()
        second = self.make_memory()
        paths = [scan.video.path, first.photo.path, second.photo.path]
        self.assertTrue(all(os.path.exists(p) for p in paths))
        self.place.delete()
        self.assertEqual(Scan.objects.count(), 0)
        self.assertEqual(Memory.objects.count(), 0)
        self.assertFalse(any(os.path.exists(p) for p in paths))


# --- Pin and its rules ------------------------------------------------------


class PinTests(ModelTestCase):
    def setUp(self):
        super().setUp()
        self.scan = self.make_scan()
        self.memory = self.make_memory()

    def make_pin(self, **changes):
        fields = {
            "memory": self.memory,
            "scan": self.scan,
            "x": 1.62,
            "y": 1.08,
            "z": 1.41,
            "placed_by": "user",
        }
        fields.update(changes)
        return Pin.objects.create(**fields)

    def test_pin_in_same_place_saves(self):
        pin = self.make_pin()
        pin.refresh_from_db()
        self.assertEqual((pin.x, pin.y, pin.z), (1.62, 1.08, 1.41))
        self.assertEqual(pin.placed_by, Pin.PlacedBy.USER)

    def test_pin_across_places_refused(self):
        other_place = Place.objects.create(owner=self.ana, name="Flat")
        other_scan = self.make_scan(place=other_place)
        with self.assertRaisesMessage(ValidationError, "must belong to the same place"):
            self.make_pin(scan=other_scan)
        self.assertEqual(Pin.objects.count(), 0)

    def test_second_pin_same_scan_refused(self):
        self.make_pin()
        with self.assertRaises(ValidationError):
            self.make_pin(x=0.0)
        self.assertEqual(Pin.objects.count(), 1)

    def test_one_pin_per_scan_allowed(self):
        second_scan = self.make_scan()
        self.make_pin()
        self.make_pin(scan=second_scan, placed_by="ai")
        self.assertEqual(self.memory.pins.count(), 2)

    def test_placed_by_must_be_stated(self):
        for value in ("", "none"):
            with self.assertRaises(ValidationError):
                self.make_pin(placed_by=value)
        self.assertEqual(Pin.objects.count(), 0)

    def test_coordinates_must_be_numbers(self):
        with self.assertRaisesMessage(ValidationError, "three real numbers"):
            self.make_pin(x=float("nan"))
        with self.assertRaisesMessage(ValidationError, "three real numbers"):
            self.make_pin(z=float("inf"))
        self.assertEqual(Pin.objects.count(), 0)

    def test_delete_scan_removes_pins_keeps_memory(self):
        self.make_pin()
        self.scan.delete()
        self.assertEqual(Pin.objects.count(), 0)
        self.assertTrue(Memory.objects.filter(pk=self.memory.pk).exists())

    def test_delete_memory_removes_pins(self):
        self.make_pin()
        self.memory.delete()
        self.assertEqual(Pin.objects.count(), 0)
        self.assertTrue(Scan.objects.filter(pk=self.scan.pk).exists())

    def test_delete_place_removes_pins(self):
        self.make_pin()
        self.place.delete()
        self.assertEqual(Pin.objects.count(), 0)
