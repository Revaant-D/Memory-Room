"""Tests for `manage.py import_room`: bringing a room built in Colab into the app.

The rooms here are written by hand: a room.json, a run.json and a three-point
PLY in exactly the layout the AI code writes (ai/roomgeom/pointsfile.py).
"""

import io
import json
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

from django.core.management import CommandError, call_command

from rooms.models import Memory, Pin, Place, Scan
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user, video_file

REAL_MODEL = "facebook/map-anything-apache"
STAND_IN = "MADE-UP ROOM: stand-in model, not a reconstruction"

PLY_HEADER = (
    "ply\n"
    "format binary_little_endian 1.0\n"
    "comment Memory Room: metres, floor at z = 0, z up\n"
    "element vertex {n}\n"
    "property float x\n"
    "property float y\n"
    "property float z\n"
    "property uchar red\n"
    "property uchar green\n"
    "property uchar blue\n"
    "end_header\n"
)
POINTS = [(0.0, 0.0, 0.0, 200, 10, 10), (4.0, 3.0, 2.5, 10, 200, 10), (1.0, 1.0, 1.0, 10, 10, 200)]


def ply_bytes(points=POINTS, count=None, header=PLY_HEADER):
    n = len(points) if count is None else count
    return header.format(n=n).encode("ascii") + b"".join(struct.pack("<fffBBB", *p) for p in points)


def room_json(**changes):
    room = {
        "version": 1,
        "frames_used": 60,
        "n_points": 3,
        "has_colors": True,
        "box": {"low": [0.0, 0.0, 0.0], "high": [4.0, 3.0, 2.5]},
        "up_consistency": 0.97,
        "wall_aligned": False,
        "voxel_m": 0.02,
        "points_files": {"bin": "points.bin", "ply": "points.ply"},
        "anchors": [],
        "model_info": {"model_id": REAL_MODEL, "weights_revision": "00f9c24", "precision": "fp16"},
    }
    room.update(changes)
    return room


# What a stand-in run writes in room.json (ai/roompipe/fake.py).
STAND_IN_ROOM = room_json(model_info={"model_id": "stand-in (made-up room, not a reconstruction)"})


def run_json(**changes):
    run = {
        "run_name": "room-2026-11-18",
        "stand_in": False,
        "model_id": REAL_MODEL,
        "weights_revision": "00f9c24",
        "gpu": "Tesla T4",
        "precision_used": "fp16",
        "finished": True,
        "stopped_because": None,
    }
    run.update(changes)
    return run


class ImportRoomTests(TempMediaTestCase):
    def setUp(self):
        self.place = Place.objects.create(owner=make_user("ana"), name="First flat")
        self.scan = Scan.objects.create(place=self.place, video=video_file())
        self.work = Path(tempfile.mkdtemp(prefix="memory-room-test-room-"))
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)

    # --- helpers ---

    def write_room(self, folder=None, room=None, run=None, ply=None):
        """A room folder. Pass False for any part to leave that file out."""
        folder = folder or self.work / "room"
        folder.mkdir(parents=True, exist_ok=True)
        if room is not False:
            (folder / "room.json").write_text(json.dumps(room or room_json()), encoding="utf-8")
        if run is not False:
            (folder / "run.json").write_text(json.dumps(run or run_json()), encoding="utf-8")
        if ply is not False:
            (folder / "points.ply").write_bytes(ply_bytes() if ply is None else ply)
        return folder

    def zip_room(self, folder, inside=""):
        """Zip a room folder's files, at the top of the zip or inside one folder."""
        path = self.work / "room.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for file in folder.iterdir():
                archive.write(file, inside + file.name)
        return path

    def run_command(self, *args):
        out = io.StringIO()
        call_command("import_room", *[str(a) for a in args], stdout=out)
        return out.getvalue()

    def refused(self, *args):
        """Run the command, expect a refusal, check the scan is untouched; return the message."""
        with self.assertRaises(CommandError) as caught:
            self.run_command(*args)
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.status, Scan.Status.UPLOADED)
        self.assertFalse(self.scan.points_file)
        self.assertEqual(self.scan.room_info, {})
        return str(caught.exception)

    def assert_imported(self):
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.status, Scan.Status.READY)
        self.assertRegex(self.scan.points_file.name, r"^places/\d+/scans/[0-9a-f]{32}-points\.ply$")
        with self.scan.points_file.open("rb") as stored:
            self.assertEqual(stored.read(), ply_bytes())

    # --- a good room ---

    def test_import_folder(self):
        out = self.run_command(self.scan.pk, self.write_room())
        self.assert_imported()
        self.assertIn(f"Scan {self.scan.pk} is ready", out)
        self.assertIn("3 points", out)

    def test_room_facts_kept(self):
        self.run_command(self.scan.pk, self.write_room())
        self.scan.refresh_from_db()
        info = self.scan.room_info
        self.assertEqual(info["n_points"], 3)
        self.assertEqual(info["box"], {"low": [0.0, 0.0, 0.0], "high": [4.0, 3.0, 2.5]})
        self.assertEqual(info["up_consistency"], 0.97)
        self.assertEqual(info["frames_used"], 60)
        self.assertEqual(info["model_id"], REAL_MODEL)
        self.assertEqual(info["weights_revision"], "00f9c24")
        self.assertEqual(info["precision"], "fp16")
        self.assertEqual(info["gpu"], "Tesla T4")
        self.assertEqual(info["run_name"], "room-2026-11-18")
        self.assertIs(info["made_up"], False)

    def test_import_zip(self):
        self.run_command(self.scan.pk, self.zip_room(self.write_room()))
        self.assert_imported()

    def test_import_zip_with_one_folder_inside(self):
        self.run_command(self.scan.pk, self.zip_room(self.write_room(), inside="room-2026-11-18/"))
        self.assert_imported()

    def test_import_folder_holding_one_room_folder(self):
        self.write_room(self.work / "unzipped" / "room-2026-11-18")
        self.run_command(self.scan.pk, self.work / "unzipped")
        self.assert_imported()

    def test_import_again_replaces_the_file(self):
        self.run_command(self.scan.pk, self.write_room())
        self.scan.refresh_from_db()
        first = Path(self.scan.points_file.path)
        self.run_command(self.scan.pk, self.write_room())
        self.scan.refresh_from_db()
        self.assertNotEqual(Path(self.scan.points_file.path), first)
        self.assertTrue(Path(self.scan.points_file.path).exists())
        self.assertFalse(first.exists())

    # --- a scan that already has pins (S2, 18 Nov) ---

    def place_two_photos(self):
        for _ in range(2):
            memory = Memory.objects.create(place=self.place, photo=jpeg_file())
            Pin.objects.create(memory=memory, scan=self.scan, x=1.0, y=1.0, z=1.4, placed_by="user")

    def test_refuses_when_the_scan_has_pins(self):
        # A rebuilt room has its own frame, so the old spots would point at the wrong places.
        self.run_command(self.scan.pk, self.write_room())
        self.scan.refresh_from_db()
        before = self.scan.points_file.name
        self.place_two_photos()
        with self.assertRaises(CommandError) as caught:
            self.run_command(self.scan.pk, self.write_room())
        self.assertIn(f"Scan {self.scan.pk} has 2 placed photos", str(caught.exception))
        self.assertIn("--drop-pins", str(caught.exception))
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.points_file.name, before)
        self.assertEqual(Pin.objects.count(), 2)

    def test_drop_pins_replaces_and_deletes_them(self):
        self.run_command(self.scan.pk, self.write_room())
        self.place_two_photos()
        out = self.run_command(self.scan.pk, self.write_room(), "--drop-pins")
        self.assert_imported()
        self.assertEqual(Pin.objects.count(), 0)
        self.assertEqual(Memory.objects.count(), 2)  # the photos stay; only their spots go
        self.assertIn("2 placed photos lost their place", out)

    # --- refusals ---

    def test_unknown_scan(self):
        message = self.refused(999, self.write_room())
        self.assertIn("No scan number 999", message)

    def test_missing_path(self):
        message = self.refused(self.scan.pk, self.work / "not-here")
        self.assertIn("not-here", message)

    def test_failed_run_explained(self):
        run = run_json(finished=False, stopped_because="the room could not be levelled: no floor")
        message = self.refused(self.scan.pk, self.write_room(room=False, ply=False, run=run))
        self.assertIn("no room.json", message)
        self.assertIn("the room could not be levelled: no floor", message)

    def test_failed_run_beside_an_old_room_refused(self):
        # Review, 18 Nov: a rerun that failed early can leave the previous run's
        # room.json and points.ply beside its own run.json.
        run = run_json(finished=False, stopped_because="only 12 frames could be read from the video")
        message = self.refused(self.scan.pk, self.write_room(run=run))
        self.assertIn("only 12 frames could be read from the video", message)

    def test_files_from_different_runs_refused(self):
        # A stand-in room.json beside a real run.json must not pass as a real room.
        room = room_json(model_info={"model_id": "stand-in (made-up room, not a reconstruction)"})
        message = self.refused(self.scan.pk, self.write_room(room=room, run=run_json()))
        self.assertIn("disagree", message)

    def damaged_zip(self, points):
        """A zip of a good room whose points.ply has one byte flipped near its end."""
        ply = ply_bytes(points)
        folder = self.write_room(room=room_json(n_points=len(points)), ply=ply)
        path = self.work / "damaged.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for file in folder.iterdir():
                archive.write(file, file.name)
        data = bytearray(path.read_bytes())
        data[data.index(ply[-15:])] ^= 0xFF  # the last point, stored as it is
        path.write_bytes(bytes(data))
        return path

    def test_damaged_zip_refused(self):
        message = self.refused(self.scan.pk, self.damaged_zip(POINTS))
        self.assertIn("damaged", message)

    def test_damaged_zip_found_while_copying_leaves_no_file(self):
        # Review, 18 Nov: past the first 4 KB the damage only shows during the copy.
        many = [(i * 0.01, 0.5, 1.0, 10, 20, 30) for i in range(400)]  # 6,000 bytes of points
        message = self.refused(self.scan.pk, self.damaged_zip(many))
        self.assertIn("damaged", message)
        scans = Path(self.scan.video.path).parent
        self.assertEqual([p.name for p in scans.iterdir() if p.name.endswith("-points.ply")], [])

    def test_unknown_version(self):
        message = self.refused(self.scan.pk, self.write_room(room=room_json(version=2)))
        self.assertIn("version 2", message)

    def test_no_ply(self):
        message = self.refused(self.scan.pk, self.write_room(ply=False))
        self.assertIn("points.ply", message)

    def test_not_a_ply(self):
        message = self.refused(self.scan.pk, self.write_room(ply=b"hello"))
        self.assertIn("points.ply", message)

    def test_ply_with_another_layout(self):
        other = PLY_HEADER.replace("property uchar red\n", "property float nx\n")
        message = self.refused(self.scan.pk, self.write_room(ply=ply_bytes(header=other)))
        self.assertIn("layout", message)

    def test_ply_cut_short(self):
        message = self.refused(self.scan.pk, self.write_room(ply=ply_bytes(count=5)))
        self.assertIn("cut short", message)

    def test_point_counts_disagree(self):
        message = self.refused(self.scan.pk, self.write_room(room=room_json(n_points=7)))
        self.assertIn("7", message)

    def test_unknown_model_refused(self):
        room = room_json(model_info={})
        message = self.refused(self.scan.pk, self.write_room(room=room, run=False))
        self.assertIn("which model", message)

    def test_non_commercial_weights_refused(self):
        room = room_json(model_info={"model_id": "facebook/map-anything"})
        run = run_json(model_id="facebook/map-anything")
        message = self.refused(self.scan.pk, self.write_room(room=room, run=run))
        self.assertIn("facebook/map-anything", message)

    # --- made-up rooms ---

    def test_made_up_room_refused(self):
        run = run_json(stand_in=True, model_id=STAND_IN, weights_revision=None, gpu=None)
        message = self.refused(self.scan.pk, self.write_room(room=STAND_IN_ROOM, run=run))
        self.assertIn("--made-up", message)

    def test_made_up_room_seen_in_room_json(self):
        # `python -m roompipe demo` writes no run.json; its room.json still says what made it.
        room = room_json(model_info={"model_id": "stand-in (made-up room, not a reconstruction)"})
        message = self.refused(self.scan.pk, self.write_room(room=room, run=False))
        self.assertIn("--made-up", message)

    def test_made_up_room_with_flag(self):
        run = run_json(stand_in=True, model_id=STAND_IN, weights_revision=None, gpu=None)
        out = self.run_command(self.scan.pk, self.write_room(room=STAND_IN_ROOM, run=run), "--made-up")
        self.assert_imported()
        self.assertIs(self.scan.room_info["made_up"], True)
        self.assertIn("MADE-UP ROOM", out)

    def test_made_up_flag_on_a_real_room_refused(self):
        message = self.refused(self.scan.pk, self.write_room(), "--made-up")
        self.assertIn("--made-up", message)

    # --- finding the scan's number ---

    def test_admin_scan_list_shows_the_number(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("admin", password="pass-12345-word")
        self.client.login(username="admin", password="pass-12345-word")
        response = self.client.get("/admin/rooms/scan/")
        self.assertContains(response, "column-id")  # the header of the "Id" column
