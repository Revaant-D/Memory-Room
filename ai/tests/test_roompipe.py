"""Tests for roompipe, using the stand-in model. No GPU, no real video, no real photo.

Run from prebuilt/ai/pipeline with a Python that has numpy (and, for two
tests that are otherwise skipped, opencv and Pillow):

    python -m unittest discover -s tests

What these prove: given model output of a stated accuracy, the steps around
the model (levelling, files, anchors, the two tries, pin or ask, batching)
do the right thing. What they cannot prove: anything about the real model.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `import roompipe` works when run from elsewhere

import numpy as np  # noqa: E402

import roompipe  # noqa: E402,F401  (also puts roomgeom on the path)
from roomgeom.level import Refilm  # noqa: E402
from roomgeom.pointsfile import read_bin, read_ply  # noqa: E402

from roompipe.build import build_room, load_room  # noqa: E402
from roompipe.fake import DEMO_PHOTOS, ROOM_SIZE, FakeRoomModel, camera, demo_room, make_demo, walk_around  # noqa: E402
from roompipe.model import (  # noqa: E402
    MODEL_ID,
    ModelOutput,
    amp_dtype_for,
    invalid_output_problem,
    run_mapanything,
)
from roompipe.place import place_photos, summary_lines  # noqa: E402


class PipeTestCase(unittest.TestCase):
    """A made-up room, 60 frame files, some photo files, and a stand-in model that knows them."""

    spacing = 0.06  # coarse points keep the tests quick

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.dir = Path(self.folder.name)
        self.points, self.colors = demo_room(spacing=self.spacing)
        self.truth, self.frames, self.photos = {}, [], []
        for i, pose in enumerate(walk_around()):
            path = self.dir / f"f{i:04d}.jpg"
            path.write_bytes(b"frame")
            self.truth[path.name] = pose
            self.frames.append(path)
        for name, (position, forward) in DEMO_PHOTOS.items():
            self.add_photo(name, position, forward)

    def tearDown(self):
        self.folder.cleanup()

    def add_photo(self, name, position, forward):
        path = self.dir / name
        path.write_bytes(b"photo")
        self.truth[name] = camera(position, forward)
        self.photos.append(path)

    def model(self, **kwargs):
        return FakeRoomModel(self.truth, self.points, self.colors, **kwargs)

    def build(self, model, **kwargs):
        return build_room(self.frames, model, self.dir / "room", **kwargs)

    def expected_in_room(self, model, true_position):
        """Where a true position should land in the built room's frame.

        The build call (the model's first) answered in its own frame; the
        room frame is that frame levelled. Both moves are known here, so the
        right answer can be worked out and compared with what was stored.
        """
        Q, shift, scale = model.moves[0]
        in_model_frame = scale * Q @ np.asarray(true_position, dtype=float) + shift
        anchor = load_room(self.dir / "room")["anchors"][0]
        # Recover the room's rotation and shift from one anchor it already holds.
        anchor_model = np.eye(4)
        anchor_model[:3, :3] = Q @ self.truth[Path(anchor["file"]).name][:3, :3]
        anchor_model[:3, 3] = scale * Q @ self.truth[Path(anchor["file"]).name][:3, 3] + shift
        anchor_room = np.array(anchor["pose"])
        R = anchor_room[:3, :3] @ anchor_model[:3, :3].T
        t = anchor_room[:3, 3] - R @ anchor_model[:3, 3]
        return R @ in_model_frame + t


class BuildTests(PipeTestCase):
    def test_room_folder_holds_everything(self):
        room = self.build(self.model())
        folder = self.dir / "room"
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["anchors", "points.bin", "points.ply", "room.json"])
        self.assertEqual(room, load_room(folder))
        self.assertEqual(room["frames_used"], 60)
        self.assertEqual(len(room["anchors"]), 20)
        self.assertTrue(room["has_colors"])
        self.assertAlmostEqual(room["up_consistency"], 1.0, places=3)
        for anchor in room["anchors"]:
            self.assertTrue((folder / anchor["file"]).is_file())
        self.assertEqual(room["anchors"][1]["file"], "anchors/f0003.jpg")

    def test_points_are_levelled_thinned_and_the_same_in_both_files(self):
        room = self.build(self.model(), voxel=0.05)
        points, colors = read_bin(self.dir / "room" / "points.bin")
        ply_points, ply_colors = read_ply(self.dir / "room" / "points.ply")
        np.testing.assert_array_equal(points, ply_points)
        np.testing.assert_array_equal(colors, ply_colors)
        self.assertEqual(len(points), room["n_points"])
        self.assertLess(len(points), len(self.points))  # thinned
        self.assertLess(abs(np.percentile(points[:, 2], 1)), 0.01)  # the floor is at z = 0
        self.assertAlmostEqual(float(np.percentile(points[:, 2], 99.9)), ROOM_SIZE[2], delta=0.01)
        low, high = room["box"]["low"], room["box"]["high"]
        self.assertAlmostEqual(high[2] - low[2], ROOM_SIZE[2], delta=0.05)

    def test_colours_follow_their_points(self):
        # The floor is brown and the ceiling near white; after levelling and
        # thinning, low points must still be brown and high points pale.
        self.build(self.model())
        points, colors = read_bin(self.dir / "room" / "points.bin")
        # The floor finder is good to half a centimetre, so look within 2 cm.
        floor = colors[np.abs(points[:, 2]) < 0.02].mean(axis=0)
        ceiling = colors[np.abs(points[:, 2] - ROOM_SIZE[2]) < 0.02].mean(axis=0)
        self.assertLess(floor[2], 110)  # little blue: brown
        self.assertGreater(ceiling.min(), 200)

    def test_anchor_poses_are_in_the_room_frame(self):
        model = self.model()
        room = self.build(model)
        for anchor in room["anchors"]:
            pose = np.array(anchor["pose"])
            self.assertAlmostEqual(pose[2, 3], 1.5, delta=0.01)  # camera height above the floor
            self.assertAlmostEqual(pose[2, 2], 0.0, delta=1e-6)  # looking level
            np.testing.assert_allclose(pose[:3, :3] @ pose[:3, :3].T, np.eye(3), atol=1e-9)

    def test_one_format_only(self):
        room = self.build(self.model(), formats=("ply",))
        self.assertFalse((self.dir / "room" / "points.bin").exists())
        self.assertEqual(room["points_files"], {"ply": "points.ply"})

    def test_wall_alignment_is_passed_through(self):
        room = self.build(self.model(), align_walls=True)
        size = np.array(room["box"]["high"]) - np.array(room["box"]["low"])
        np.testing.assert_allclose(size, ROOM_SIZE, atol=0.15)
        self.assertTrue(room["wall_aligned"])

    def test_a_model_with_no_colours_still_builds(self):
        room = self.build(FakeRoomModel(self.truth, self.points, None))
        self.assertFalse(room["has_colors"])
        _, colors = read_bin(self.dir / "room" / "points.bin")
        self.assertTrue((colors == 128).all())

    def test_wrong_number_of_poses_is_an_error(self):
        def short_model(paths):
            out = self.model()(paths)
            return ModelOutput(out.points, out.colors, out.poses[:-1])

        with self.assertRaises(ValueError):
            self.build(short_model)

    def test_tilted_video_is_refused(self):
        rolls = np.where(np.arange(60) % 2 == 0, 75.0, -75.0)
        for path, pose in zip(self.frames, walk_around(roll_deg=rolls)):
            self.truth[path.name] = pose
        with self.assertRaises(Refilm):
            self.build(self.model())


class PlaceTests(PipeTestCase):
    def test_exact_model_places_every_photo_exactly(self):
        model = self.model()
        self.build(model)
        model.scale_range = (0.8, 1.25)  # each placement pass comes back at a different size
        results = place_photos(self.dir / "room", self.photos, model)
        self.assertEqual([r["photo"] for r in results], list(DEMO_PHOTOS))
        for result, (position, _) in zip(results, DEMO_PHOTOS.values()):
            self.assertEqual(result["placed_by"], "ai")
            self.assertEqual(result["reason"], "")
            expected = self.expected_in_room(model, position)
            np.testing.assert_allclose([result["x"], result["y"], result["z"]], expected, atol=1e-6)
            # Height above the floor survives, to the half centimetre the floor finder gives.
            self.assertAlmostEqual(result["z"], position[2], delta=0.006)
            self.assertLess(result["gap_m"], 1e-6)

    def test_a_slightly_noisy_model_still_pins_close_to_the_truth(self):
        model = self.model(pose_noise=0.01, seed=5)
        self.build(model)
        model.scale_range = (0.8, 1.25)
        results = place_photos(self.dir / "room", self.photos, model)
        for result, (position, _) in zip(results, DEMO_PHOTOS.values()):
            self.assertEqual(result["placed_by"], "ai", result["reason"])
            expected = self.expected_in_room(model, position)
            self.assertLess(np.linalg.norm([result["x"], result["y"], result["z"]] - expected), 0.10)

    def test_a_photo_the_model_is_unsure_about_is_not_pinned(self):
        model = self.model(jump={"on-the-bed.jpg": 1.6})
        self.build(model)  # call 1; the placement tries are calls 2 and 3
        model.calls.append([])  # line the two tries up as "first" and "second"
        model.moves.append(model.moves[0])
        results = {r["photo"]: r for r in place_photos(self.dir / "room", self.photos, model)}
        self.assertIsNone(results["on-the-bed.jpg"]["placed_by"])
        self.assertEqual(results["on-the-bed.jpg"]["reason"], "two tries 1.6 m apart")
        self.assertEqual(sum(r["placed_by"] == "ai" for r in results.values()), 4)

    def test_a_photo_taken_outside_the_room_is_not_pinned(self):
        self.add_photo("the-corridor.jpg", [-2.5, 1.0, 1.5], [1.0, 0.0, 0.0])
        model = self.model()
        self.build(model, align_walls=True)
        results = {r["photo"]: r for r in place_photos(self.dir / "room", self.photos, model)}
        self.assertEqual(results["the-corridor.jpg"]["reason"], "the spot is outside the room")
        self.assertIsNone(results["the-corridor.jpg"]["placed_by"])
        self.assertEqual(results["by-the-window.jpg"]["placed_by"], "ai")

    def test_many_photos_go_through_in_batches_and_stay_in_order(self):
        rng = np.random.default_rng(1)
        self.photos = []
        for i in range(23):
            self.add_photo(f"p{i:02d}.jpg", rng.uniform([0.5, 0.5, 1.0], [3.5, 2.5, 1.8]), [1.0, 0.2, 0.0])
        model = self.model()
        self.build(model)
        results = place_photos(self.dir / "room", self.photos, model)
        self.assertEqual([r["photo"] for r in results], [f"p{i:02d}.jpg" for i in range(23)])
        placement_calls = model.calls[1:]
        self.assertEqual(len(placement_calls), 6)  # 3 batches, two tries each
        self.assertEqual([len(c) for c in placement_calls], [20, 20, 20, 20, 13, 13])  # 10 anchors + photos
        self.assertTrue(all(r["placed_by"] == "ai" for r in results))

    def test_the_two_tries_use_different_anchors(self):
        model = self.model()
        self.build(model)
        place_photos(self.dir / "room", self.photos[:1], model)
        first, second = (set(call[:10]) for call in model.calls[1:])
        self.assertEqual(len(first), 10)
        self.assertFalse(first & second)

    def test_results_are_saved_as_plain_json(self):
        self.truth["by-the-window.jpg"] = np.full((4, 4), np.nan)  # a model that returns nonsense
        model = self.model()
        self.build(model)
        results = place_photos(self.dir / "room", self.photos, model)
        text = (self.dir / "room" / "placements.json").read_text(encoding="utf-8")
        self.assertNotIn("NaN", text)
        self.assertEqual(json.loads(text), results)
        broken = results[0]
        self.assertIsNone(broken["placed_by"])
        self.assertEqual((broken["x"], broken["y"], broken["z"]), (None, None, None))
        self.assertEqual(broken["reason"], "the model's answer was not a real position")
        self.assertEqual(results[1]["placed_by"], "ai")  # one bad photo does not spoil the rest

    def test_save_can_be_turned_off(self):
        model = self.model()
        self.build(model)
        place_photos(self.dir / "room", self.photos, model, save=False)
        self.assertFalse((self.dir / "room" / "placements.json").exists())

    def test_too_few_anchors(self):
        self.frames = self.frames[:5]
        model = self.model()
        room = self.build(model)
        self.assertEqual(len(room["anchors"]), 5)
        with self.assertRaises(ValueError):
            place_photos(self.dir / "room", self.photos, model)

    def test_anchors_on_a_line_pin_nothing_and_say_why(self):
        # Someone filmed walking straight across the room.
        for i, path in enumerate(self.frames):
            self.truth[path.name] = camera([0.5 + 3.0 * i / 59, 1.5, 1.5], [0.0, 1.0, 0.0])
        model = self.model()
        self.build(model)
        results = place_photos(self.dir / "room", self.photos, model)
        self.assertTrue(all(r["placed_by"] is None for r in results))
        self.assertIn("one line", results[0]["reason"])

    def test_summary(self):
        model = self.model()
        self.build(model)
        lines = summary_lines(place_photos(self.dir / "room", self.photos, model))
        self.assertEqual(len(lines), 7)  # a heading, five photos, a total
        self.assertIn("pinned", lines[1])
        self.assertEqual(lines[-1], "5 of 5 pinned; the rest need the person to place them.")


class ModelRuleTests(unittest.TestCase):
    def test_model_id_is_the_apache_one(self):
        self.assertEqual(MODEL_ID, "facebook/map-anything-apache")

    def test_other_weights_are_refused_before_anything_is_loaded(self):
        with self.assertRaisesRegex(ValueError, "only the Apache weights"):
            run_mapanything(["x.jpg"], model_id="facebook/map-anything")

    def test_an_unknown_precision_is_refused_before_anything_is_loaded(self):
        with self.assertRaisesRegex(ValueError, "precision must be one of"):
            run_mapanything(["x.jpg"], precision="int8")


class PrecisionTests(unittest.TestCase):
    """The number format: bf16 only where the GPU has it, and a clear stop on NaN."""

    def test_a_t4_gets_fp16(self):
        self.assertEqual(amp_dtype_for(7), "fp16")  # T4 is compute capability 7.5

    def test_ampere_and_newer_get_bf16(self):
        for major in (8, 9, 10):
            self.assertEqual(amp_dtype_for(major), "bf16")

    def test_good_output_has_no_problem(self):
        self.assertIsNone(invalid_output_problem(np.tile(np.eye(4), (3, 1, 1)), 1000, 5, "fp16"))

    def test_nan_poses_are_a_problem_that_names_the_fix(self):
        poses = np.tile(np.eye(4), (3, 1, 1))
        poses[1, 0, 3] = np.nan
        problem = invalid_output_problem(poses, 1000, 0, "fp16")
        self.assertIn("camera positions", problem)
        self.assertIn('PRECISION = "fp32"', problem)

    def test_many_nan_points_are_a_problem(self):
        problem = invalid_output_problem(np.tile(np.eye(4), (3, 1, 1)), 1000, 11, "fp16")
        self.assertIn("11 of 1,000 points", problem)

    def test_no_points_at_all_is_a_problem(self):
        self.assertIn("no points", invalid_output_problem(np.tile(np.eye(4), (3, 1, 1)), 0, 0, "fp16"))

    def test_fp32_does_not_suggest_fp32(self):
        poses = np.full((2, 4, 4), np.nan)
        self.assertNotIn("Set PRECISION", invalid_output_problem(poses, 10, 0, "fp32"))


class DemoTests(unittest.TestCase):
    def test_make_demo(self):
        with tempfile.TemporaryDirectory() as folder:
            room, results = make_demo(folder, spacing=0.06)
            self.assertEqual(len(room["anchors"]), 20)
            self.assertEqual(len(results), 5)
            self.assertTrue(all(r["placed_by"] == "ai" for r in results))
            self.assertTrue((Path(folder) / "room" / "placements.json").is_file())
            self.assertEqual(len(list((Path(folder) / "frames").iterdir())), 60)

    def test_command_line_demo(self):
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run(
                [sys.executable, "-m", "roompipe", "demo", "--out", folder, "--spacing", "0.06"],
                cwd=HERE.parent, capture_output=True, text=True,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("MADE-UP ROOM", done.stdout)
            self.assertIn("5 of 5 pinned", done.stdout)


class FrameTests(unittest.TestCase):
    def test_sharp_frames_are_picked_from_a_video(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("opencv is not installed")
        from roompipe.frames import extract_frames

        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "room.mp4"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 30, (160, 120))
            if not writer.isOpened():
                self.skipTest("this opencv build cannot write a test video")
            rng = np.random.default_rng(0)
            for i in range(90):
                # Even frames are sharp (noise); odd frames are flat grey, as if blurred.
                frame = rng.integers(0, 256, (120, 160, 3), dtype=np.uint8) if i % 2 == 0 else np.full((120, 160, 3), 128, np.uint8)
                writer.write(frame)
            writer.release()

            paths = extract_frames(video, Path(folder) / "frames", n_frames=10)
            self.assertEqual([p.name for p in paths], [f"f{i:04d}.jpg" for i in range(10)])
            for path in paths:
                picked = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                self.assertEqual(picked.shape, (120, 160))
                self.assertGreater(picked.std(), 20)  # a sharp frame was kept, never a flat one
            with self.assertRaises(ValueError):
                extract_frames(Path(folder) / "missing.mp4", Path(folder) / "none")


if __name__ == "__main__":
    unittest.main()
