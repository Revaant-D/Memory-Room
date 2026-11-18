"""Tests for roomgeom, on a made-up room whose true shape is known.

Run from prebuilt/ai/geometry with a Python that has numpy:

    python -m unittest discover -s tests

Every test builds its own data. Nothing here touches the reconstruction
model, a GPU, a video or a photo.
"""

import unittest

import numpy as np

from roomgeom.fit import apply_fit, fit_residuals, on_a_line, spread, umeyama
from roomgeom.level import (
    Refilm,
    estimate_up,
    level_room,
    pick_anchors,
    room_rotation,
    voxel_downsample,
)
from roomgeom.place import Thresholds, check_two_tries, inside, place_from_poses, split_anchors

ROOM = np.array([4.0, 3.0, 2.5])  # width, depth, height in metres
CAMERA_HEIGHT = 1.5


def rotation(rng):
    """A random proper rotation (no mirror)."""
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def camera(position, forward, roll_deg=0.0):
    """A 4 x 4 camera-to-world pose (OpenCV: +Z forward, +Y down in the image)."""
    forward = np.asarray(forward, dtype=float)
    forward = forward / np.linalg.norm(forward)
    down = np.array([0.0, 0.0, -1.0])
    down = down - forward * (down @ forward)
    down /= np.linalg.norm(down)
    right = np.cross(down, forward)
    roll = np.radians(roll_deg)
    right, down = (
        np.cos(roll) * right + np.sin(roll) * down,
        -np.sin(roll) * right + np.cos(roll) * down,
    )
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = right, down, forward, position
    return pose


def walk_around(n=60, roll_deg=None):
    """n cameras on a circle in the middle of the room, each looking outward."""
    centre = np.array([ROOM[0] / 2, ROOM[1] / 2, CAMERA_HEIGHT])
    poses = []
    for i, angle in enumerate(np.linspace(0, 2 * np.pi, n, endpoint=False)):
        out = np.array([np.cos(angle), np.sin(angle), 0.0])
        roll = 0.0 if roll_deg is None else roll_deg[i]
        poses.append(camera(centre + 0.8 * out, out, roll))
    return np.stack(poses)


def room_points(rng):
    """Points on the floor (dense), the ceiling and the four walls of the room."""
    gx, gy = np.meshgrid(np.arange(0, ROOM[0], 0.05), np.arange(0, ROOM[1], 0.05))
    floor = np.column_stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)])
    ceiling = np.column_stack([rng.uniform(0, ROOM[0], 800), rng.uniform(0, ROOM[1], 800), np.full(800, ROOM[2])])
    walls = []
    for axis, value in ((0, 0.0), (0, ROOM[0]), (1, 0.0), (1, ROOM[1])):
        wall = rng.uniform(0, 1, size=(1000, 3)) * ROOM
        wall[:, axis] = value
        walls.append(wall)
    return np.vstack([floor, ceiling, *walls]), len(floor), len(ceiling)


def move(points, poses, Q, shift, scale=1.0):
    """Put points and poses into another frame: rotate by Q, scale, then shift."""
    moved_points = scale * points @ Q.T + shift
    moved_poses = poses.copy()
    moved_poses[:, :3, :3] = Q @ poses[:, :3, :3]
    moved_poses[:, :3, 3] = scale * poses[:, :3, 3] @ Q.T + shift
    return moved_points, moved_poses


class FitTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(1)

    def test_recovers_a_known_move_exactly(self):
        src = self.rng.normal(size=(12, 3))
        Q, shift, scale = rotation(self.rng), np.array([3.0, -2.0, 0.5]), 1.7
        dst = scale * src @ Q.T + shift
        s, R, t = umeyama(src, dst)
        self.assertAlmostEqual(s, scale, places=9)
        np.testing.assert_allclose(R, Q, atol=1e-9)
        np.testing.assert_allclose(t, shift, atol=1e-9)
        self.assertLess(fit_residuals(s, R, t, src, dst).max(), 1e-9)

    def test_small_noise_gives_small_error(self):
        src = self.rng.normal(size=(20, 3))
        Q = rotation(self.rng)
        dst = 0.9 * src @ Q.T + 1.0 + self.rng.normal(scale=0.01, size=(20, 3))
        s, R, t = umeyama(src, dst)
        self.assertLess(fit_residuals(s, R, t, src, dst).max(), 0.05)
        self.assertAlmostEqual(s, 0.9, delta=0.02)

    def test_never_a_mirror_image_even_for_flat_points(self):
        # Cameras that walked round a room at one height all lie in a plane.
        # A point off that plane must land on the correct side of it.
        flat = np.column_stack([self.rng.normal(size=(10, 2)), np.zeros(10)])
        Q, shift = rotation(self.rng), np.array([1.0, 2.0, 3.0])
        s, R, t = umeyama(flat, flat @ Q.T + shift)
        self.assertAlmostEqual(np.linalg.det(R), 1.0, places=9)
        above = np.array([0.2, -0.1, 0.4])
        np.testing.assert_allclose(apply_fit(s, R, t, above), above @ Q.T + shift, atol=1e-9)

    def test_refuses_bad_input(self):
        good = self.rng.normal(size=(5, 3))
        with self.assertRaises(ValueError):
            umeyama(good[:2], good[:2])  # too few
        with self.assertRaises(ValueError):
            umeyama(good, good[:4])  # not matching
        bad = good.copy()
        bad[0, 0] = np.nan
        with self.assertRaises(ValueError):
            umeyama(bad, good)
        with self.assertRaises(ValueError):
            umeyama(np.ones((5, 3)), good)  # all in one spot

    def test_spread_and_line(self):
        circle = walk_around()[:, :3, 3]
        first, second, third = spread(circle)
        self.assertAlmostEqual(first, 0.8 / np.sqrt(2), places=6)
        self.assertAlmostEqual(second, 0.8 / np.sqrt(2), places=6)
        self.assertAlmostEqual(third, 0.0, places=6)
        self.assertFalse(on_a_line(circle))
        line = np.column_stack([np.linspace(0, 3, 10), np.zeros(10), np.full(10, 1.5)])
        self.assertTrue(on_a_line(line))


class LevelTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(2)
        self.points, self.n_floor, self.n_ceiling = room_points(self.rng)
        self.poses = walk_around()
        # What the model would hand back: the same room in an arbitrary frame.
        self.Q, self.shift = rotation(self.rng), np.array([5.0, -3.0, 2.0])
        self.raw_points, self.raw_poses = move(self.points, self.poses, self.Q, self.shift)

    def test_up_is_found(self):
        up, consistency = estimate_up(self.raw_poses)
        np.testing.assert_allclose(up, self.Q @ [0, 0, 1.0], atol=1e-9)
        self.assertAlmostEqual(consistency, 1.0, places=9)

    def test_room_rotation_is_a_rotation_with_up_as_z(self):
        for up in (self.Q @ [0, 0, 1.0], [0, 0, 1.0], [0, 0, -1.0], [1.0, 0, 0]):
            R = room_rotation(up)
            np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-12)
            self.assertAlmostEqual(np.linalg.det(R), 1.0, places=12)
            np.testing.assert_allclose(R @ np.asarray(up, dtype=float), [0, 0, 1.0], atol=1e-12)

    def test_floor_lands_on_zero_and_ceiling_at_room_height(self):
        out = level_room(self.raw_points, self.raw_poses, voxel=0.02)
        room = self.raw_points @ out["R"].T
        room[:, 2] -= out["floor_h"]
        floor_z = room[: self.n_floor, 2]
        ceiling_z = room[self.n_floor : self.n_floor + self.n_ceiling, 2]
        self.assertLess(np.abs(floor_z).max(), 0.006)  # within the 1 cm slice
        self.assertLess(np.abs(ceiling_z - ROOM[2]).max(), 0.006)

    def test_cameras_end_up_at_camera_height_looking_level(self):
        out = level_room(self.raw_points, self.raw_poses)
        heights = out["room_poses"][:, 2, 3]
        self.assertLess(np.abs(heights - CAMERA_HEIGHT).max(), 0.006)
        forward_z = out["room_poses"][:, 2, 2]  # z part of each camera's forward direction
        self.assertLess(np.abs(forward_z).max(), 1e-9)

    def test_shapes_are_not_stretched(self):
        out = level_room(self.raw_points, self.raw_poses)
        low, high = out["box"]
        self.assertAlmostEqual(high[2] - low[2], ROOM[2], delta=0.05)
        centres = out["room_poses"][:, :3, 3]
        self.assertAlmostEqual(np.linalg.norm(centres[0] - centres[30]), 1.6, places=9)

    def test_without_wall_alignment_the_box_is_bigger_than_the_room(self):
        # The design as written. The room sits at an angle in its own frame,
        # so the box around it overstates the room. This test records that.
        low, high = level_room(self.raw_points, self.raw_poses)["box"]
        floor_area = (high[0] - low[0]) * (high[1] - low[1])
        self.assertGreater(floor_area, ROOM[0] * ROOM[1] * 1.2)

    def test_wall_alignment_makes_the_box_fit_the_room(self):
        out = level_room(self.raw_points, self.raw_poses, align_walls=True)
        low, high = out["box"]
        np.testing.assert_allclose(high - low, ROOM, atol=0.12)  # long side along x
        # Still a rotation, still level, and the cameras moved with the points.
        np.testing.assert_allclose(out["R"] @ out["R"].T, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(out["R"]), 1.0, places=12)
        self.assertLess(np.abs(out["room_poses"][:, 2, 3] - CAMERA_HEIGHT).max(), 0.006)
        middle = out["room_poses"][:, :3, 3].mean(0)
        np.testing.assert_allclose(middle[:2], ((low + high) / 2)[:2], atol=0.05)
        # One floor corner is the origin, so positions read as distances along the walls.
        np.testing.assert_allclose(low[:2], [0.0, 0.0], atol=0.03)
        np.testing.assert_allclose(middle[:2], [ROOM[0] / 2, ROOM[1] / 2], atol=0.08)
        # The same move is available for anything else that needs it.
        again = self.raw_points @ out["R"].T - [*out["origin_xy"], out["floor_h"]]
        np.testing.assert_allclose(again[out["keep"]], out["room_points"], atol=1e-9)

    def test_without_wall_alignment_the_origin_is_left_alone(self):
        out = level_room(self.raw_points, self.raw_poses)
        np.testing.assert_array_equal(out["origin_xy"], [0.0, 0.0])

    def test_thinning_keeps_one_point_per_cube_and_is_repeatable(self):
        out = level_room(self.raw_points, self.raw_poses, voxel=0.10)
        cubes = np.floor(out["room_points"] / 0.10).astype(np.int64)
        self.assertEqual(len(np.unique(cubes, axis=0)), len(cubes))
        self.assertLess(len(out["keep"]), len(self.raw_points))
        again = level_room(self.raw_points, self.raw_poses, voxel=0.10)
        np.testing.assert_array_equal(out["keep"], again["keep"])
        direct = voxel_downsample(self.points, 0.10)
        self.assertEqual(len(direct), len(np.unique(np.floor(self.points / 0.10), axis=0)))

    def test_anchors(self):
        self.assertEqual(level_room(self.raw_points, self.raw_poses)["anchors"], list(range(0, 60, 3)))
        self.assertEqual(pick_anchors(10), list(range(10)))
        self.assertEqual(pick_anchors(0), [])
        self.assertEqual(len(pick_anchors(200)), 20)

    def test_tilted_phone_is_refused(self):
        rolls = np.where(np.arange(60) % 2 == 0, 75.0, -75.0)  # rolled hard left, then right
        _, tilted = move(self.points, walk_around(roll_deg=rolls), self.Q, self.shift)
        with self.assertRaises(Refilm):
            level_room(self.raw_points, tilted)

    def test_no_floor_in_view_is_refused(self):
        no_floor = self.raw_points[self.points[:, 2] > 1.2]
        with self.assertRaises(Refilm):
            level_room(no_floor, self.raw_poses)


class PlaceTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(3)
        self.anchors = walk_around()[::3]  # 20 anchors, already in the room frame
        self.box = (np.zeros(3), ROOM)
        # Three photos taken at known spots, at heights different from the anchors.
        self.photos = np.stack(
            [
                camera([1.0, 1.0, 1.2], [1.0, 0.2, 0.0]),
                camera([3.2, 2.0, 1.7], [-1.0, 1.0, -0.2]),
                camera([2.0, 0.5, 1.0], [0.0, -1.0, 0.1]),
            ]
        )

    def model_run(self, anchor_ids, noise=0.0, photos=None):
        """What one model pass would return: anchors then photos, in a frame of its own."""
        photos = self.photos if photos is None else photos
        views = np.concatenate([self.anchors[anchor_ids], photos])
        Q, shift, scale = rotation(self.rng), self.rng.normal(size=3) * 4, self.rng.uniform(0.5, 2.0)
        _, run = move(np.zeros((1, 3)), views, Q, shift, scale)
        run[:, :3, 3] += self.rng.normal(scale=noise, size=(len(run), 3)) if noise else 0.0
        return run

    def one_try(self, anchor_ids, **kwargs):
        return place_from_poses(self.model_run(anchor_ids, **kwargs), self.anchors[anchor_ids])

    def test_split(self):
        even, odd = split_anchors(20)
        self.assertEqual(even, list(range(0, 20, 2)))
        self.assertEqual(odd, list(range(1, 20, 2)))

    def test_exact_poses_place_photos_exactly(self):
        even, _ = split_anchors(len(self.anchors))
        found, residual = self.one_try(even)
        self.assertLess(residual, 1e-9)
        for (position, facing), truth in zip(found, self.photos):
            np.testing.assert_allclose(position, truth[:3, 3], atol=1e-9)
            np.testing.assert_allclose(facing, truth[:3, 2], atol=1e-9)

    def test_good_tries_are_pinned(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even, noise=0.01)
        b, rb = self.one_try(odd, noise=0.01)
        results = check_two_tries(a, ra, b, rb, self.box)
        self.assertEqual([r["placed_by"] for r in results], ["ai", "ai", "ai"])
        self.assertEqual([r["reason"] for r in results], ["", "", ""])
        for result, truth in zip(results, self.photos):
            self.assertLess(np.linalg.norm(result["pos"] - truth[:3, 3]), 0.15)

    def test_tries_that_disagree_on_position_are_not_pinned(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even)
        moved = self.photos.copy()
        moved[0, :3, 3] += [1.6, 0.0, 0.0]  # the second try puts photo 0 somewhere else
        b, rb = self.one_try(odd, photos=moved)
        results = check_two_tries(a, ra, b, rb, self.box)
        self.assertIsNone(results[0]["placed_by"])
        self.assertEqual(results[0]["reason"], "two tries 1.6 m apart")
        self.assertEqual(results[1]["placed_by"], "ai")

    def test_tries_that_disagree_on_direction_are_not_pinned(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even)
        turned = self.photos.copy()
        turned[1] = camera(self.photos[1][:3, 3], [1.0, 1.0, -0.2])  # same spot, facing 90° away
        b, rb = self.one_try(odd, photos=turned)
        results = check_two_tries(a, ra, b, rb, self.box)
        self.assertIsNone(results[1]["placed_by"])
        self.assertIn("degrees apart", results[1]["reason"])
        self.assertGreater(results[1]["turn_deg"], 30)

    def test_a_spot_outside_the_room_is_not_pinned(self):
        outside = self.photos.copy()
        outside[2, :3, 3] = [6.0, 0.5, 1.0]  # two metres beyond the far wall
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even, photos=outside)
        b, rb = self.one_try(odd, photos=outside)
        results = check_two_tries(a, ra, b, rb, self.box)
        self.assertEqual(results[2]["reason"], "the spot is outside the room")
        self.assertIsNone(results[2]["placed_by"])

    def test_the_pinned_spot_itself_must_be_inside_the_room(self):
        # Review, 18 Nov: the check looked at the first try only, but the pin goes
        # at the middle of the two tries, which can be further out.
        face = np.array([1.0, 0.0, 0.0])
        a = [(np.array([4.29, 1.0, 1.0]), face)]  # just inside the 0.3 m margin past x = 4
        b = [(np.array([4.98, 1.0, 1.0]), face)]  # 0.69 m further out: the tries still "agree"
        results = check_two_tries(a, 0.0, b, 0.0, self.box)
        self.assertEqual(results[0]["reason"], "the spot is outside the room")
        self.assertIsNone(results[0]["placed_by"])

    def test_margin_allows_a_spot_just_past_the_wall(self):
        self.assertTrue(inside([4.2, 1.0, 1.0], self.box, margin=0.3))
        self.assertFalse(inside([4.4, 1.0, 1.0], self.box, margin=0.3))
        self.assertFalse(inside([4.2, 1.0, 1.0], self.box))

    def test_anchors_that_do_not_line_up_block_every_photo(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even, noise=0.3)  # a bad run: anchors scattered
        b, rb = self.one_try(odd)
        self.assertGreater(ra, 0.15)
        results = check_two_tries(a, ra, b, rb, self.box)
        self.assertTrue(all(r["placed_by"] is None for r in results))
        self.assertIn("anchors lined up only", results[0]["reason"])

    def test_not_a_number_is_never_pinned(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even)
        b, rb = self.one_try(odd)
        a[0] = (np.array([np.nan, 1.0, 1.0]), a[0][1])
        results = check_two_tries(a, ra, b, rb, self.box)
        self.assertIsNone(results[0]["placed_by"])
        self.assertEqual(results[0]["reason"], "the model's answer was not a real position")

    def test_thresholds_can_be_changed(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even, noise=0.01)
        b, rb = self.one_try(odd, noise=0.01)
        strict = Thresholds(gap_m=0.0001)
        self.assertTrue(all(r["placed_by"] is None for r in check_two_tries(a, ra, b, rb, self.box, strict)))

    def test_anchors_on_a_line_are_refused(self):
        line = np.stack([camera([x, 1.5, 1.5], [0.0, 1.0, 0.0]) for x in np.linspace(0.5, 3.5, 8)])
        run = np.concatenate([line, self.photos])
        with self.assertRaises(ValueError):
            place_from_poses(run, line)

    def test_uneven_tries_are_an_error(self):
        even, odd = split_anchors(len(self.anchors))
        a, ra = self.one_try(even)
        b, rb = self.one_try(odd)
        with self.assertRaises(ValueError):
            check_two_tries(a, ra, b[:2], rb, self.box)


if __name__ == "__main__":
    unittest.main()
