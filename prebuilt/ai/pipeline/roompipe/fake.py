"""A stand-in for the reconstruction model, and a made-up room for it to "see".

Two uses:

1. Tests. `FakeRoomModel` behaves like the real model in the ways the rest
   of roompipe depends on: every call answers in a brand-new frame (its own
   origin, rotation and, if asked, scale), with poses in the order the images
   were given. It knows the true pose of every image by its file name. That
   lets the whole build-and-place path be tested with known right answers.

2. A demo room. `make_demo(folder)` writes a complete room folder (points,
   anchors, placements) for a made-up 4 m x 3 m bedroom, so a viewer has
   something to show before any real room exists.

NOTHING HERE IS EVIDENCE ABOUT THE REAL MODEL. The fake model is as accurate
as it is told to be. A demo room must never be presented as a reconstruction.
"""

from pathlib import Path

import numpy as np

from roompipe.model import ModelOutput

ROOM_SIZE = np.array([4.0, 3.0, 2.5])  # width (x), depth (y), height (z), metres
CAMERA_HEIGHT = 1.5


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
    centre = np.array([ROOM_SIZE[0] / 2, ROOM_SIZE[1] / 2, CAMERA_HEIGHT])
    poses = []
    for i, angle in enumerate(np.linspace(0, 2 * np.pi, n, endpoint=False)):
        out = np.array([np.cos(angle), np.sin(angle), 0.0])
        poses.append(camera(centre + 0.8 * out, out, 0.0 if roll_deg is None else roll_deg[i]))
    return np.stack(poses)


def _patch(rng, origin, side_a, side_b, color, spacing, shade=12):
    """Random points on a flat rectangle: origin + s * side_a + t * side_b."""
    side_a, side_b = np.asarray(side_a, dtype=float), np.asarray(side_b, dtype=float)
    area = np.linalg.norm(np.cross(side_a, side_b))
    n = max(4, int(area / spacing**2))
    st = rng.uniform(0, 1, size=(n, 2))
    points = np.asarray(origin, dtype=float) + st[:, :1] * side_a + st[:, 1:] * side_b
    colors = np.clip(np.asarray(color) + rng.integers(-shade, shade + 1, size=(n, 1)), 0, 255)
    return points, colors.astype(np.uint8)


def _box(rng, low, high, color, spacing):
    """The top and four sides of a box standing on the floor."""
    (x0, y0, z0), (x1, y1, z1) = low, high
    faces = [
        ((x0, y0, z1), (x1 - x0, 0, 0), (0, y1 - y0, 0)),  # top
        ((x0, y0, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0)),
        ((x0, y1, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0)),
        ((x0, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0)),
        ((x1, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0)),
    ]
    return [_patch(rng, o, a, b, color, spacing) for o, a, b in faces]


def demo_room(spacing=0.02, seed=7):
    """A made-up bedroom. Returns (points N x 3, colors N x 3) in its true frame:
    metres, floor at z = 0, z up, one corner at the origin."""
    rng = np.random.default_rng(seed)
    W, D, H = ROOM_SIZE
    parts = [
        _patch(rng, (0, 0, 0), (W, 0, 0), (0, D, 0), (150, 111, 78), spacing),  # floor
        _patch(rng, (0, 0, H), (W, 0, 0), (0, D, 0), (236, 234, 228), spacing * 2),  # ceiling
        _patch(rng, (0, 0, 0), (W, 0, 0), (0, 0, H), (226, 220, 206), spacing),  # wall y = 0
        _patch(rng, (0, D, 0), (W, 0, 0), (0, 0, H), (214, 222, 214), spacing),  # wall y = D
        _patch(rng, (0, 0, 0), (0, D, 0), (0, 0, H), (222, 214, 204), spacing),  # wall x = 0
        _patch(rng, (W, 0, 0), (0, D, 0), (0, 0, H), (216, 216, 226), spacing),  # wall x = W
        _patch(rng, (1.2, D - 0.01, 1.0), (1.4, 0, 0), (0, 0, 1.1), (120, 170, 220), spacing),  # window
        _patch(rng, (0.01, 0.4, 0.0), (0, 0.9, 0), (0, 0, 2.0), (120, 84, 60), spacing),  # door
        _patch(rng, (0.4, 0.01, 1.2), (0.9, 0, 0), (0, 0, 0.6), (196, 90, 70), spacing),  # poster
    ]
    parts += _box(rng, (1.9, 0.05, 0.0), (3.9, 1.0, 0.5), (60, 110, 110), spacing)  # bed
    parts += _box(rng, (2.9, 2.3, 0.0), (3.95, 2.95, 0.75), (140, 100, 60), spacing)  # desk
    return np.vstack([p for p, _ in parts]), np.vstack([c for _, c in parts])


# Where the demo's photos were "taken": name -> (position, direction faced).
DEMO_PHOTOS = {
    "by-the-window.jpg": ([1.9, 2.4, 1.5], [0.0, 1.0, 0.0]),
    "on-the-bed.jpg": ([2.9, 0.6, 1.0], [-1.0, 0.6, 0.0]),
    "at-the-desk.jpg": ([3.2, 2.2, 1.2], [0.4, 1.0, -0.2]),
    "from-the-door.jpg": ([0.4, 0.9, 1.6], [1.0, 0.3, 0.0]),
    "the-poster.jpg": ([0.9, 1.2, 1.5], [0.0, -1.0, 0.0]),
}


class FakeRoomModel:
    """A stand-in for the model: a function (image paths) -> ModelOutput.

    truth:       dict mapping an image's file name to its true 4 x 4 pose.
    scale_range: each call picks a scale in this range. (1, 1) behaves like a
                 perfectly metric model; (0.8, 1.25) exercises the fit.
    pose_noise:  metres of random error added to every camera position.
    jump:        dict file name -> metres. On every second call, that image's
                 position is moved this far along x: a model that gives two
                 different answers for the same photo.
    """

    def __init__(self, truth, points, colors=None, seed=0, scale_range=(1.0, 1.0), pose_noise=0.0, jump=None):
        self.truth = {name: np.asarray(pose, dtype=float) for name, pose in truth.items()}
        self.points, self.colors = np.asarray(points, dtype=float), colors
        self.rng = np.random.default_rng(seed)
        self.scale_range, self.pose_noise, self.jump = scale_range, pose_noise, jump or {}
        self.calls = []  # the file names of every call, in order
        self.moves = []  # the (Q, shift, scale) each call used: model = scale * Q @ truth + shift

    def __call__(self, image_paths):
        names = [Path(p).name for p in image_paths]
        Q, _ = np.linalg.qr(self.rng.normal(size=(3, 3)))
        if np.linalg.det(Q) < 0:
            Q[:, 0] = -Q[:, 0]
        shift = self.rng.normal(size=3) * 3.0
        scale = float(self.rng.uniform(*self.scale_range))
        second_call = len(self.calls) % 2 == 1
        self.calls.append(names)
        self.moves.append((Q, shift, scale))

        poses = []
        for name in names:
            pose = self.truth[name].copy()
            if second_call and name in self.jump:
                pose[0, 3] += self.jump[name]
            moved = np.eye(4)
            moved[:3, :3] = Q @ pose[:3, :3]
            moved[:3, 3] = scale * Q @ pose[:3, 3] + shift
            if self.pose_noise:
                moved[:3, 3] += self.rng.normal(scale=self.pose_noise, size=3)
            poses.append(moved)
        return ModelOutput(
            points=scale * self.points @ Q.T + shift, colors=self.colors, poses=np.stack(poses)
        )


def _placeholder_image(path, color):
    """A small stand-in picture, so the folder holds real image files."""
    try:
        from PIL import Image

        Image.new("RGB", (96, 72), tuple(int(c) for c in color)).save(path, "JPEG")
    except ImportError:
        Path(path).write_bytes(b"placeholder: this demo was made without Pillow\n")


def make_demo(out_dir, spacing=0.02, align_walls=False, pose_noise=0.01, seed=7):
    """Write a complete made-up room folder. Returns (room dict, placement results).

    Layout: <out_dir>/frames/ (60 stand-in frames), <out_dir>/photos/ (5
    stand-in photos), <out_dir>/room/ (the room folder, with placements.json).
    """
    from roompipe.build import build_room
    from roompipe.place import place_photos

    out_dir = Path(out_dir)
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)
    (out_dir / "photos").mkdir(parents=True, exist_ok=True)
    points, colors = demo_room(spacing=spacing, seed=seed)

    truth, frames, photos = {}, [], []
    for i, pose in enumerate(walk_around()):
        path = out_dir / "frames" / f"f{i:04d}.jpg"
        _placeholder_image(path, (200, 200 - i * 2, 160))
        truth[path.name] = pose
        frames.append(path)
    for name, (position, forward) in DEMO_PHOTOS.items():
        path = out_dir / "photos" / name
        _placeholder_image(path, (90, 140, 200))
        truth[name] = camera(position, forward)
        photos.append(path)

    model = FakeRoomModel(truth, points, colors, seed=seed, pose_noise=pose_noise)
    room = build_room(frames, model, out_dir / "room", align_walls=align_walls)
    model.scale_range = (0.8, 1.25)  # placement passes come back at slightly different sizes
    results = place_photos(out_dir / "room", photos, model)
    return room, results
