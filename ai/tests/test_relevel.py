"""Tests for re-levelling a room folder that was levelled wrongly (roompipe.relevel).

The first real room (18 Nov 2026) was built before the floor fix: its bed
top was taken for the floor. Its model output is fine, so the room is
corrected on the laptop instead of on the GPU again.

Each test builds a correct room with the stand-in model, breaks its
levelling in a known way (tipped 2 degrees, dropped 0.7 m) in every file,
and checks that re-levelling gives the correct room back. Run from ai/
with a Python that has numpy, Pillow and matplotlib:

    python -m unittest discover -s tests
"""

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

import roompipe  # noqa: E402,F401
from roomgeom.pointsfile import READERS, WRITERS  # noqa: E402
from roompipe.__main__ import main  # noqa: E402
from roompipe.build import build_room  # noqa: E402
from roompipe.fake import FakeRoomModel, demo_room, walk_around  # noqa: E402
from roompipe.relevel import relevel_room_folder  # noqa: E402

try:
    from PIL import Image
    import matplotlib  # noqa: F401

    HAVE_EXTRAS = True
except ImportError:  # pragma: no cover
    HAVE_EXTRAS = False

DROP = 0.7
AXIS = np.array([1.0, 0.5, 0.0]) / np.linalg.norm([1.0, 0.5, 0.0])
_K = np.array([[0, -AXIS[2], AXIS[1]], [AXIS[2], 0, -AXIS[0]], [-AXIS[1], AXIS[0], 0]])
TIP = np.eye(3) + np.sin(np.radians(2.0)) * _K + (1 - np.cos(np.radians(2.0))) * _K @ _K


def wrong(points):
    """Where a right point lands in the broken room: dropped, then tipped."""
    return (np.asarray(points, dtype=float) - [0, 0, DROP]) @ TIP.T


def wrong_pose(pose):
    pose = np.array(pose, dtype=float)
    out = pose.copy()
    out[:3, :3] = TIP @ pose[:3, :3]
    out[:3, 3] = wrong(pose[:3, 3][None])[0]
    return out


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=1), encoding="utf-8")


def break_levelling(folder):
    """Move every room-frame number in `folder` into the broken frame."""
    folder = Path(folder)
    room = read_json(folder / "room.json")
    for kind, name in room["points_files"].items():
        points, colors = READERS[kind](folder / name)
        WRITERS[kind](folder / name, wrong(points), colors)
    for anchor in room["anchors"]:
        anchor["pose"] = wrong_pose(anchor["pose"]).tolist()
    move = room["model_to_room"]  # room = model @ R.T - offset
    offset = np.array([*move["origin_xy"], move["floor_h"]])
    new_offset = (offset + [0, 0, DROP]) @ TIP.T
    move["R"] = (TIP @ np.array(move["R"])).tolist()
    move["origin_xy"], move["floor_h"] = new_offset[:2].tolist(), float(new_offset[2])
    room["box"] = {"low": [0, 0, 0], "high": [1, 1, 1]}  # stale on purpose
    write_json(folder / "room.json", room)

    cameras = read_json(folder / "cameras.json")
    for camera in cameras["cameras"]:
        camera["pose"] = wrong_pose(camera["pose"]).tolist()
    write_json(folder / "cameras.json", cameras)

    with np.load(folder / "dense.npz") as dense:
        arrays = {key: dense[key] for key in dense.files}
    shape = arrays["points"].shape
    arrays["points"] = wrong(arrays["points"].astype(float).reshape(-1, 3)).reshape(shape).astype(np.float16)
    np.savez_compressed(folder / "dense.npz", **arrays)

    placements = read_json(folder / "placements.json")
    for entry in placements:
        if entry["x"] is not None:
            entry["x"], entry["y"], entry["z"] = wrong([[entry["x"], entry["y"], entry["z"]]])[0].tolist()
            entry["facing"] = (TIP @ entry["facing"]).tolist()
    write_json(folder / "placements.json", placements)


def fingerprint(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(folder).rglob("*")) if p.is_file()}


@unittest.skipUnless(HAVE_EXTRAS, "needs Pillow and matplotlib")
class RelevelFolderTests(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.dir = Path(self._folder.name)
        frames = []
        for i in range(60):
            path = self.dir / "frames" / f"f{i:04d}.jpg"
            path.parent.mkdir(exist_ok=True)
            Image.new("RGB", (64, 36), (200, 200 - i, 160)).save(path)
            frames.append(path)
        points, colors = demo_room(spacing=0.06)
        truth = {p.name: pose for p, pose in zip(frames, walk_around(len(frames)))}
        self.model = FakeRoomModel(truth, points, colors, view_size=(20, 12))
        self.good = self.dir / "good"
        self.room = build_room(frames, self.model, self.good)
        write_json(self.good / "placements.json", [
            {"photo": "a.jpg", "placed_by": "ai", "x": 1.0, "y": 1.5, "z": 1.4, "facing": [1.0, 0.0, 0.0],
             "gap_m": 0.05},
            {"photo": "b.jpg", "placed_by": None, "reason": "ask", "x": None, "y": None, "z": None,
             "facing": None},
        ])
        self.bad = self.dir / "bad"
        shutil.copytree(self.good, self.bad)
        break_levelling(self.bad)
        self.out = self.dir / "fixed"

    def tearDown(self):
        self._folder.cleanup()

    def assert_same_room(self, fixed, good):
        for kind, name in read_json(good / "room.json")["points_files"].items():
            np.testing.assert_allclose(READERS[kind](fixed / name)[0], READERS[kind](good / name)[0], atol=0.005)
        fixed_room, good_room = read_json(fixed / "room.json"), read_json(good / "room.json")
        for a, b in zip(fixed_room["anchors"], good_room["anchors"], strict=True):
            np.testing.assert_allclose(a["pose"], b["pose"], atol=0.005)
        for side in ("low", "high"):
            np.testing.assert_allclose(fixed_room["box"][side], good_room["box"][side], atol=0.01)
        # The move from the model's frame lands the model's points where the good room has them.
        model_points = self.model.moves[0][2] * demo_room(spacing=0.06)[0] @ self.model.moves[0][0].T \
            + self.model.moves[0][1]

        def to_room(move):
            return model_points @ np.array(move["R"]).T - [*move["origin_xy"], move["floor_h"]]

        np.testing.assert_allclose(to_room(fixed_room["model_to_room"]), to_room(good_room["model_to_room"]),
                                   atol=0.005)
        for a, b in zip(read_json(fixed / "cameras.json")["cameras"], read_json(good / "cameras.json")["cameras"],
                        strict=True):
            np.testing.assert_allclose(a["pose"], b["pose"], atol=0.005)
        with np.load(fixed / "dense.npz") as f, np.load(good / "dense.npz") as g:
            np.testing.assert_allclose(f["points"].astype(float), g["points"].astype(float), atol=0.02)
            np.testing.assert_array_equal(f["conf"], g["conf"])
            np.testing.assert_array_equal(f["mask"], g["mask"])
        fixed_places, good_places = read_json(fixed / "placements.json"), read_json(good / "placements.json")
        np.testing.assert_allclose([fixed_places[0][k] for k in "xyz"], [good_places[0][k] for k in "xyz"],
                                   atol=0.005)
        np.testing.assert_allclose(fixed_places[0]["facing"], good_places[0]["facing"], atol=1e-3)
        self.assertEqual(fixed_places[1], good_places[1])  # a photo with no spot stays as it was

    def test_a_wrongly_levelled_room_comes_back_right_in_every_file(self):
        relevel_room_folder(self.bad, self.out)
        self.assert_same_room(self.out, self.good)

    def test_room_json_records_what_was_done(self):
        room = relevel_room_folder(self.bad, self.out)
        self.assertEqual(room, read_json(self.out / "room.json"))
        record = room["relevelled"]
        self.assertEqual(record["up_from"], "floor")
        self.assertAlmostEqual(record["floor_tilt_deg"], 2.0, delta=0.1)
        self.assertAlmostEqual(record["floor_was_at_m"], -DROP, delta=0.01)
        self.assertEqual(record["before"]["model_to_room"], read_json(self.bad / "room.json")["model_to_room"])
        self.assertIn("at", record)
        self.assertEqual(room["up_from"], "floor")
        self.assertEqual(room["n_points"], self.room["n_points"])

    def test_the_source_is_left_alone(self):
        before = fingerprint(self.bad)
        relevel_room_folder(self.bad, self.out)
        self.assertEqual(fingerprint(self.bad), before)

    def test_a_zip_works_too(self):
        archive = self.dir / "bad.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for path in self.bad.rglob("*"):
                z.write(path, path.relative_to(self.bad).as_posix())
        relevel_room_folder(archive, self.out)
        self.assert_same_room(self.out, self.good)

    def test_a_folder_already_holding_files_is_refused(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("mine", encoding="utf-8")
        with self.assertRaises(ValueError):
            relevel_room_folder(self.bad, self.out)
        self.assertEqual([p.name for p in self.out.iterdir()], ["keep.txt"])

    def test_a_folder_with_no_room_is_refused(self):
        empty = self.dir / "empty"
        empty.mkdir()
        with self.assertRaises(ValueError):
            relevel_room_folder(empty, self.out)

    def test_command_line_writes_the_room_and_a_new_preview(self):
        self.assertEqual(main(["relevel", "--room", str(self.bad), "--out", str(self.out)]), 0)
        self.assert_same_room(self.out, self.good)
        self.assertTrue((self.out / "preview.png").is_file())
        self.assertTrue((self.out / "preview-photos.png").is_file())


if __name__ == "__main__":
    unittest.main()
