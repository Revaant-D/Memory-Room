"""Tests for what the Colab notebook relies on: the room bundle, and roompipe.session.

Run from ai/ with a Python that has numpy, opencv, Pillow and matplotlib:

    python -m unittest discover -s tests

Like the other tests here, these use the stand-in model. They show the files
and the bookkeeping are right. They say nothing about the real model.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

import roompipe  # noqa: E402,F401
from roomgeom.level import points_to_room  # noqa: E402

from roompipe.build import build_room, load_room  # noqa: E402
from roompipe.fake import FakeRoomModel, demo_room, walk_around  # noqa: E402
from roompipe.model import run_mapanything  # noqa: E402
from roompipe.place import place_photos  # noqa: E402
from roompipe import session  # noqa: E402

try:
    import cv2  # noqa: F401
    from PIL import Image
    import matplotlib  # noqa: F401

    HAVE_EXTRAS = True
except ImportError:  # pragma: no cover
    HAVE_EXTRAS = False


class Folder(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.dir = Path(self._folder.name)

    def tearDown(self):
        self._folder.cleanup()

    def frames(self, n=60):
        paths = []
        for i in range(n):
            path = self.dir / "frames" / f"f{i:04d}.jpg"
            path.parent.mkdir(exist_ok=True)
            if HAVE_EXTRAS:
                Image.new("RGB", (64, 36), (200, 200 - i, 160)).save(path)
            else:
                path.write_bytes(b"frame")
            paths.append(path)
        return paths


@unittest.skipUnless(HAVE_EXTRAS, "needs opencv, Pillow and matplotlib")
class BundleTests(Folder):
    """build_room with per-frame detail writes frames/, cameras.json and dense.npz."""

    def build(self, **kwargs):
        frames = self.frames()
        points, colors = demo_room(spacing=0.06)
        truth = {p.name: pose for p, pose in zip(frames, walk_around(len(frames)))}
        model = FakeRoomModel(truth, points, colors, view_size=(20, 12), **kwargs)
        room = build_room(frames, model, self.dir / "room")
        return room, model, frames, points

    def test_bundle_files_are_written(self):
        room, _, frames, _ = self.build()
        out = self.dir / "room"
        self.assertEqual(room["bundle"], {"frames": "frames/", "cameras": "cameras.json", "dense": "dense.npz"})
        self.assertEqual(len(list((out / "frames").glob("*.jpg"))), len(frames))
        cameras = json.loads((out / "cameras.json").read_text(encoding="utf-8"))
        self.assertEqual((cameras["width"], cameras["height"]), (20, 12))
        self.assertEqual(len(cameras["cameras"]), len(frames))
        self.assertIn("OpenCV", cameras["convention"])
        with np.load(out / "dense.npz") as dense:
            self.assertEqual(dense["points"].shape, (len(frames), 12, 20, 3))
            self.assertEqual(dense["conf"].shape, (len(frames), 12, 20))
            self.assertEqual(dense["mask"].dtype, bool)

    def test_every_camera_matches_the_anchor_poses(self):
        room, *_ = self.build()
        cameras = json.loads((self.dir / "room" / "cameras.json").read_text(encoding="utf-8"))["cameras"]
        for anchor in room["anchors"]:
            np.testing.assert_allclose(cameras[anchor["frame"]]["pose"], anchor["pose"])

    def test_model_to_room_puts_the_true_floor_at_zero(self):
        """The stored move, applied to the model's own points, lands the floor at z = 0."""
        room, model, _, points = self.build()
        Q, shift, scale = model.moves[0]
        in_model_frame = scale * points @ Q.T + shift
        move = room["model_to_room"]
        in_room = points_to_room(in_model_frame, np.array(move["R"]), move["floor_h"], np.array(move["origin_xy"]))
        floor = in_room[np.isclose(points[:, 2], 0.0)]
        self.assertLess(np.abs(floor[:, 2]).max(), 0.02)

    def test_dense_points_are_in_the_room_frame(self):
        room, *_ = self.build()
        low, high = np.array(room["box"]["low"]), np.array(room["box"]["high"])
        with np.load(self.dir / "room" / "dense.npz") as dense:
            pts = dense["points"].astype(float).reshape(-1, 3)
        self.assertGreater(pts[:, 2].min(), -0.05)
        self.assertLess(pts[:, 2].max(), high[2] + 0.2)
        self.assertTrue(np.all(pts[:, :2] > low[:2] - 0.3) and np.all(pts[:, :2] < high[:2] + 0.3))

    def test_without_detail_no_bundle_is_written(self):
        frames = self.frames()
        points, colors = demo_room(spacing=0.06)
        truth = {p.name: pose for p, pose in zip(frames, walk_around(len(frames)))}
        room = build_room(frames, FakeRoomModel(truth, points, colors), self.dir / "room")
        self.assertEqual(room["bundle"], {})
        self.assertFalse((self.dir / "room" / "dense.npz").exists())


class PickTests(unittest.TestCase):
    def test_even_subset_keeps_ends_and_order(self):
        items = list(range(60))
        picked = session.pick_evenly(items, 40)
        self.assertEqual(len(picked), 40)
        self.assertEqual((picked[0], picked[-1]), (0, 59))
        self.assertEqual(picked, sorted(picked))

    def test_asking_for_more_than_there_are(self):
        self.assertEqual(session.pick_evenly([1, 2, 3], 60), [1, 2, 3])


class OutOfMemory(RuntimeError):
    """Named like torch.cuda.OutOfMemoryError."""


OutOfMemory.__name__ = "OutOfMemoryError"


class FallbackTests(Folder):
    def test_out_of_memory_is_recognised(self):
        self.assertTrue(session.is_out_of_memory(OutOfMemory("CUDA error")))
        self.assertTrue(session.is_out_of_memory(RuntimeError("CUDA out of memory. Tried to allocate 2 GiB")))
        self.assertFalse(session.is_out_of_memory(ValueError("bad image")))

    def model_that_fits(self, most):
        frames = self.frames()
        points, colors = demo_room(spacing=0.08)
        truth = {p.name: pose for p, pose in zip(frames, walk_around(len(frames)))}
        fake = FakeRoomModel(truth, points, colors)
        seen = []

        def run(paths):
            seen.append(len(paths))
            if len(paths) > most:
                raise OutOfMemory("CUDA out of memory")
            return fake(paths)

        return frames, run, seen

    def test_retries_with_fewer_frames(self):
        frames, run, seen = self.model_that_fits(40)
        freed = []
        room, attempts = session.build_with_fallback(frames, run, self.dir / "room",
                                                     after_failure=lambda: freed.append(1))
        self.assertEqual(seen, [60, 40])
        self.assertEqual([a["ok"] for a in attempts], [False, True])
        self.assertEqual(room["frames_used"], 40)
        self.assertEqual(freed, [1])

    def test_gives_up_after_the_last_size(self):
        frames, run, seen = self.model_that_fits(10)
        with self.assertRaises(MemoryError):
            session.build_with_fallback(frames, run, self.dir / "room")
        self.assertEqual(seen, [60, 40, 30])

    def test_other_errors_are_not_retried(self):
        frames, _, _ = self.model_that_fits(60)

        def broken(paths):
            raise ValueError("the image loader read 59 of 60 images")

        with self.assertRaisesRegex(ValueError, "59 of 60"):
            session.build_with_fallback(frames, broken, self.dir / "room")

    def test_a_failed_try_leaves_nothing_behind(self):
        frames, run, _ = self.model_that_fits(40)
        stale = self.dir / "room" / "left-over.txt"
        stale.parent.mkdir()
        stale.write_text("from an earlier try")
        session.build_with_fallback(frames, run, self.dir / "room")
        self.assertFalse(stale.exists())


class RunLogTests(Folder):
    def test_steps_are_timed_and_saved(self):
        peaks = iter([1.5e9])
        log = session.RunLog(peak_memory=lambda: next(peaks), reset_memory=lambda: None, video="room.mp4")
        with log.step("model"):
            pass
        path = log.save(self.dir)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["video"], "room.mp4")
        self.assertTrue(data["steps"]["model"]["ok"])
        self.assertEqual(data["steps"]["model"]["peak_gpu_gb"], 1.5)
        self.assertIn("model", log.table())

    def test_model_calls_are_written_down_including_failures(self):
        log = session.RunLog()

        def model(paths):
            if len(paths) > 2:
                raise OutOfMemory("CUDA out of memory")
            return "output"

        run = log.wrap_model(model, "build")
        self.assertEqual(run(["a", "b"]), "output")
        with self.assertRaises(OutOfMemory):
            run(["a", "b", "c"])
        calls = log.data["model_calls"]
        self.assertEqual([(c["images"], c["ok"]) for c in calls], [(2, True), (3, False)])
        self.assertIn("out of memory", calls[1]["error"])
        self.assertTrue(all("seconds" in c for c in calls))

    def test_a_failed_step_is_written_down_and_raised(self):
        log = session.RunLog()
        with self.assertRaises(ValueError):
            with log.step("frames"):
                raise ValueError("cannot open video")
        self.assertFalse(log.data["steps"]["frames"]["ok"])
        self.assertIn("cannot open video", log.data["steps"]["frames"]["error"])


@unittest.skipUnless(HAVE_EXTRAS, "needs Pillow")
class PhotoTests(Folder):
    def exif_photo(self, name, orientation=6, focal_35=26):
        image = Image.new("RGB", (80, 40), (10, 20, 30))
        exif = Image.Exif()
        exif[0x0112] = orientation  # rotate 90 degrees when shown
        exif[0x8825] = {1: "N", 2: (40.0, 6.0, 0.0)}  # a GPS position
        exif.get_ifd(0x8769)[0xA405] = focal_35
        exif.get_ifd(0x8769)[0x9003] = "2024:05:01 18:30:00"
        path = self.dir / name
        image.save(path, exif=exif)
        return path

    def test_photos_come_out_upright_with_no_exif(self):
        source = self.exif_photo("a.jpg")
        [entry] = session.prepare_photos([source], self.dir / "ready")
        self.assertEqual(entry["size"], [40, 80])  # turned upright
        self.assertEqual(entry["shape"], "portrait")
        self.assertEqual(entry["focal_35mm"], 26.0)
        self.assertEqual(entry["taken"], "2024:05:01 18:30:00")
        with Image.open(self.dir / "ready" / entry["file"]) as out:
            self.assertEqual(len(out.getexif()), 0)  # no GPS, no anything

    def test_png_becomes_jpeg_and_clashing_names_are_kept_apart(self):
        Image.new("RGBA", (30, 20)).save(self.dir / "same.png")
        Image.new("RGB", (30, 20)).save(self.dir / "same.jpg")
        entries = session.prepare_photos([self.dir / "same.png", self.dir / "same.jpg"], self.dir / "ready")
        names = sorted(e["file"] for e in entries)
        self.assertEqual(len(set(names)), 2)
        self.assertTrue(all(n.endswith(".jpg") for n in names))

    def test_an_unreadable_photo_is_reported_not_dropped(self):
        bad = self.dir / "broken.jpg"
        bad.write_bytes(b"not a picture")
        [entry] = session.prepare_photos([bad], self.dir / "ready")
        self.assertIsNone(entry["file"])
        self.assertIn("skipped", entry)


@unittest.skipUnless(HAVE_EXTRAS, "needs opencv, Pillow and matplotlib")
class RehearsalTests(Folder):
    """The notebook's whole path with the stand-in: frames -> room -> photos -> pictures."""

    def test_dry_run_end_to_end(self):
        frames = self.frames()
        photos = []
        for name in ("by-the-window.jpg", "on-the-bed.jpg", "at-the-desk.jpg", "the-poster.jpg"):
            Image.new("RGB", (40, 30)).save(self.dir / name)
            photos.append(self.dir / name)
        model = session.rehearsal_model([p.name for p in frames], [p.name for p in photos])
        room, attempts = session.build_with_fallback(frames, model, self.dir / "room")
        self.assertTrue(attempts[-1]["ok"])
        self.assertTrue((self.dir / "room" / "dense.npz").exists())
        self.assertIn("points from 60 frames", session.room_summary(room))
        results = place_photos(self.dir / "room", photos, model)
        self.assertEqual(len(results), 4)
        sheet = session.frames_sheet(frames, self.dir / "sheet.png")
        preview = session.preview_png(self.dir / "room", self.dir / "preview.png", results,
                                      label=session.STAND_IN_LABEL)
        self.assertGreater(sheet.stat().st_size, 1000)
        self.assertGreater(preview.stat().st_size, 1000)
        self.assertEqual(load_room(self.dir / "room")["model_info"]["model_id"],
                         "stand-in (made-up room, not a reconstruction)")

    def test_video_facts(self):
        import cv2

        path = self.dir / "clip.mp4"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (64, 48))
        for i in range(45):
            writer.write(np.full((48, 64, 3), i * 5 % 255, dtype=np.uint8))
        writer.release()
        facts = session.video_facts(path)
        self.assertEqual(facts["stored_size"], [64, 48])
        self.assertAlmostEqual(facts["seconds"], 1.5, delta=0.1)


class ModelGuardTests(unittest.TestCase):
    def test_files_the_model_cannot_read_are_refused_before_loading(self):
        with self.assertRaisesRegex(ValueError, "convert"):
            run_mapanything(["photo.heic"])


if __name__ == "__main__":
    unittest.main()
