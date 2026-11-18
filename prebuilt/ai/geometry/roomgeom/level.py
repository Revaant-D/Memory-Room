"""Turning the model's raw points into "the room frame".

The reconstruction model returns points and camera positions in a frame of
its own choosing: the floor can be tilted at any angle. The app stores
everything in one agreed frame instead:

    the floor is z = 0,  z points up,  units are metres.

Pins, anchors and later scans are all kept in this frame, so nothing moves
when a page reloads.

`estimate_up`, `floor_height` and `voxel_downsample` are the functions from
docs/reference/stage1.py, copied so this folder runs on its own. The rest
follows the T5 technical design sketch "Level, thin, keep anchors".

A camera pose here is a 4 x 4 camera-to-world matrix in the OpenCV
convention: column 3 is the camera's position, +Z looks forward out of the
lens, +Y points down in the image.
"""

import numpy as np


class Refilm(ValueError):
    """The video cannot be levelled reliably; the person should film again."""


def estimate_up(poses):
    """Which way is up, judged from how the phone was held.

    Up is minus the average of the cameras' "down in the image" direction.
    This works because the frames are upright and a phone filming a room is
    held roughly vertical.

    Returns (up, consistency). up is a unit vector. consistency is near 1
    when every frame agrees and falls as the phone tilts; below about 0.8
    the answer should not be trusted.
    """
    poses = np.asarray(poses, dtype=float)
    down = poses[:, :3, 1]
    mean = down.mean(axis=0)
    strength = float(np.linalg.norm(mean))
    if strength < 1e-9:
        raise Refilm("the camera directions cancel out; up cannot be found")
    return -mean / strength, strength


def floor_height(points, up, camera_positions):
    """The height of the floor along `up`: the fullest 1 cm slice well below the cameras."""
    heights = np.asarray(points, dtype=float) @ up
    below = heights[heights < np.median(np.asarray(camera_positions, dtype=float) @ up) - 0.5]
    if len(below) < 100:
        raise Refilm("almost no points below the camera; did the video show the floor?")
    counts, edges = np.histogram(below, bins=np.arange(below.min(), below.max() + 0.01, 0.01))
    fullest = int(np.argmax(counts))
    return float((edges[fullest] + edges[fullest + 1]) / 2)


def voxel_downsample(points, voxel=0.02, rng=None):
    """Thin the points: keep one point per small cube of side `voxel` metres.

    Returns the indices of the points to keep (so colours and anything else
    stored per point can be thinned the same way). The same input always
    gives the same answer.
    """
    points = np.asarray(points, dtype=float)
    rng = rng or np.random.default_rng(0)
    order = rng.permutation(len(points))
    cubes = np.floor(points[order] / voxel).astype(np.int64)
    _, first = np.unique(cubes, axis=0, return_index=True)
    return np.sort(order[first])


def room_rotation(up):
    """The 3 x 3 rotation that turns the model's frame so that `up` becomes +z.

    Which way the room's x axis points is arbitrary (a room has no north);
    it is fixed here by a rule so the same input always gives the same frame.
    """
    up = np.asarray(up, dtype=float)
    up = up / np.linalg.norm(up)
    x = np.cross(up, [0.0, 0.0, 1.0])
    if np.linalg.norm(x) < 0.1:  # up is already nearly +z or -z
        x = np.cross(up, [0.0, 1.0, 0.0])
    x /= np.linalg.norm(x)
    y = np.cross(up, x)
    return np.stack([x, y, up])  # rows: the room's x, y, z written in the model's frame


def points_to_room(points, R, floor_h, origin_xy=(0.0, 0.0)):
    """Move N x 3 points from the model's frame into the room frame."""
    room = np.asarray(points, dtype=float) @ R.T
    room[:, 2] -= floor_h
    room[:, :2] -= origin_xy
    return room


def poses_to_room(poses, R, floor_h, origin_xy=(0.0, 0.0)):
    """Move N camera poses (4 x 4, camera-to-world) into the room frame."""
    poses = np.asarray(poses, dtype=float)
    out = poses.copy()
    out[:, :3, :3] = R @ poses[:, :3, :3]
    out[:, :3, 3] = poses[:, :3, 3] @ R.T
    out[:, 2, 3] -= floor_h
    out[:, :2, 3] -= origin_xy
    return out


def room_box(room_points, trim_percent=1.0):
    """The box the room fits in: (lowest corner, highest corner), each x, y, z.

    The outermost 1% of points on each side is ignored, so a few stray
    points seen through a window do not stretch the box.
    """
    room_points = np.asarray(room_points, dtype=float)
    low = np.percentile(room_points, trim_percent, axis=0)
    high = np.percentile(room_points, 100.0 - trim_percent, axis=0)
    return low, high


def wall_aligned_turn(room_points, step_deg=0.5, trim_percent=1.0):
    """A turn about the z axis that lines the room's walls up with the x and y axes.

    NOT in the technical design; added here after a test showed why it
    matters. `room_rotation` points the x axis in an arbitrary direction, so
    a rectangular room usually sits at an angle in its own frame, and the box
    around it (`room_box`) is larger than the room: a 4 m x 3 m room turned
    45 degrees gets a 4.9 m x 4.9 m box. The "is the photo inside the room"
    check then lets through spots well outside the walls.

    The method: try every turn from 0 to 90 degrees and keep the one whose
    box has the smallest floor area. For a room with straight walls that is
    the turn that lines the walls up. The longer side is put along x.

    Returns a 3 x 3 rotation to apply after `room_rotation`:
    `aligned = room_points @ turn.T`. It leaves z alone.
    """
    xy = np.asarray(room_points, dtype=float)[:, :2]
    best = None
    for degrees in np.arange(0.0, 90.0, step_deg):
        a = np.radians(degrees)
        turn = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        turned = xy @ turn.T
        size = np.percentile(turned, 100.0 - trim_percent, axis=0) - np.percentile(turned, trim_percent, axis=0)
        if best is None or size[0] * size[1] < best[0]:
            best = (size[0] * size[1], turn, size)
    _, turn, size = best
    if size[1] > size[0]:  # put the long side along x: one more quarter turn
        turn = np.array([[0.0, -1.0], [1.0, 0.0]]) @ turn
    full = np.eye(3)
    full[:2, :2] = turn
    return full


def pick_anchors(n_frames, about=20):
    """Which frames to keep as anchors: evenly spaced, about `about` of them.

    60 frames give every third frame, 20 anchors, as in the design.
    """
    if n_frames <= 0:
        return []
    step = max(1, round(n_frames / about))
    return list(range(0, n_frames, step))


def level_room(points, poses, voxel=0.02, least_consistency=0.8, align_walls=False):
    """The whole "level, thin, keep anchors" step.

    points: N x 3 from the model.  poses: F x 4 x 4, one per frame used.

    align_walls: off by default, which is exactly the technical design. When
    on, the room is also turned so its walls run along x and y (see
    `wall_aligned_turn`), which makes the room's box fit the room, and one
    floor corner of that box is made the origin. A position then reads as
    "x metres along the long wall, y metres along the short one, z metres
    up", where otherwise x and y are measured from wherever the model's own
    origin happened to fall.

    Returns a dict:
        keep          indices into `points` of the points kept after thinning
        room_points   those points in the room frame (floor z = 0, z up)
        room_poses    every frame's pose in the room frame
        anchors       indices of the frames to keep as anchors
        box           (low corner, high corner) of the room
        R, floor_h, origin_xy
                      the rotation, floor height and floor origin used, to move
                      anything else with points_to_room / poses_to_room
        consistency   how well the frames agreed on which way is up (0 to 1)

    Raises Refilm when up cannot be trusted or the floor cannot be found.
    """
    points = np.asarray(points, dtype=float)
    poses = np.asarray(poses, dtype=float)
    up, consistency = estimate_up(poses)
    if consistency < least_consistency:
        raise Refilm("the phone tilted too much for the floor to be found; film again, held upright")
    floor_h = floor_height(points, up, poses[:, :3, 3])
    R = room_rotation(up)
    room = points_to_room(points, R, floor_h)
    origin_xy = np.zeros(2)
    if align_walls:
        R = wall_aligned_turn(room) @ R
        room = points_to_room(points, R, floor_h)
        origin_xy = room_box(room)[0][:2]  # the box's low corner on the floor
        room = points_to_room(points, R, floor_h, origin_xy)
    keep = voxel_downsample(room, voxel)
    room_points = room[keep]
    return {
        "keep": keep,
        "room_points": room_points,
        "room_poses": poses_to_room(poses, R, floor_h, origin_xy),
        "anchors": pick_anchors(len(poses)),
        "box": room_box(room_points),
        "R": R,
        "floor_h": floor_h,
        "origin_xy": origin_xy,
        "consistency": consistency,
    }
