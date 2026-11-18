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


def floor_layer(points, up, camera_positions):
    """Where the floor is along `up`: the lowest flat layer well below the cameras.

    The points are counted in 1 cm slices, each slice together with its two
    neighbours. A slice "stands out" when it is at least half as full as the
    fullest and twice as full as a typical slice (walls alone give typical
    slices). The floor is the lowest run of slices that stand out, not the
    fullest slice: in the first real room (18 Nov 2026) a bed top held more
    points than the floor. A floor that leans relative to `up` is spread
    over many slices; the run then covers all of them.

    Returns (low, high, peak): the run's bottom and top, and the middle of
    its fullest slice. Raises Refilm when almost nothing is below the cameras.
    """
    heights = np.asarray(points, dtype=float) @ up
    below = heights[heights < np.median(np.asarray(camera_positions, dtype=float) @ up) - 0.5]
    if len(below) < 100:
        raise Refilm("almost no points below the camera; did the video show the floor?")
    counts, edges = np.histogram(below, bins=np.arange(below.min(), below.max() + 0.02, 0.01))
    layered = np.convolve(counts, np.ones(3), mode="same")
    bar = min(layered.max(), max(0.5 * layered.max(), 2.0 * np.median(layered)))
    stands_out = layered >= bar
    first = int(np.argmax(stands_out))  # the lowest slice that stands out
    last = first
    while last + 1 < len(layered) and stands_out[last + 1]:
        last += 1
    fullest = first + int(np.argmax(layered[first : last + 1]))
    return float(edges[first]), float(edges[last + 1]), float((edges[fullest] + edges[fullest + 1]) / 2)


def floor_height(points, up, camera_positions):
    """The height of the floor along `up` (the fullest slice of `floor_layer`)."""
    return floor_layer(points, up, camera_positions)[2]


def floor_plane(points, up, low, high, most_tilt_deg=15.0, band=0.05, keep=0.02, tries=300,
                sample=50_000, seed=0):
    """The floor's own plane, found among the points of the layer from `low` to `high` along `up`.

    A robust fit (RANSAC): many planes through three points of the layer are
    tried, and the one that the most layer points lie within `keep` metres
    of wins, among planes within `most_tilt_deg` of `up`. Walls cross the
    layer, so a plain least-squares fit to the layer would be pulled by them.
    The winner is then refitted to every point within `keep` of it.

    Returns (normal, height, tilt_deg): the floor's upward direction, its
    height along that direction, and the angle from `up` to it. Returns None
    when no plane within `most_tilt_deg` of `up` holds at least 100 points.
    The same input always gives the same answer.
    """
    points = np.asarray(points, dtype=float)
    up = np.asarray(up, dtype=float) / np.linalg.norm(up)
    heights = points @ up
    layer = points[(heights > low - band) & (heights < high + band)]
    if len(layer) < 100:
        return None
    rng = np.random.default_rng(seed)
    if len(layer) > sample:
        layer = layer[rng.choice(len(layer), sample, replace=False)]
    least_cos = np.cos(np.radians(most_tilt_deg))
    best, best_count = None, 0
    for _ in range(tries):
        a, b, c = layer[rng.choice(len(layer), 3, replace=False)]
        normal = np.cross(b - a, c - a)
        length = np.linalg.norm(normal)
        if length < 1e-12:
            continue
        normal = normal / length if normal @ up >= 0 else -normal / length
        if normal @ up < least_cos:
            continue
        count = int((np.abs((layer - a) @ normal) < keep).sum())
        if count > best_count:
            best, best_count = (normal, a), count
    if best is None:
        return None
    normal, centre = best
    for _ in range(5):
        near = points[np.abs((points - centre) @ normal) < keep]
        if len(near) < 100:
            return None
        centre = near.mean(axis=0)
        refit = np.linalg.svd(near - centre, full_matrices=False)[2][-1]
        refit = refit if refit @ up >= 0 else -refit
        settled = refit @ normal > np.cos(np.radians(0.001))
        normal = refit
        if settled:
            break
    tilt = float(np.degrees(np.arccos(np.clip(normal @ up, -1.0, 1.0))))
    if tilt > most_tilt_deg:
        return None
    return normal, float(centre @ normal), tilt


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


def tilt_turn(normal):
    """The smallest rotation that turns `normal` into +z.

    Unlike `room_rotation`, it does not pick a new heading: a direction that
    is level already stays where it is as far as the tilt allows. That is
    what re-levelling a room that is already in a room frame needs.
    """
    n = np.asarray(normal, dtype=float)
    n = n / np.linalg.norm(n)
    axis = np.cross(n, [0.0, 0.0, 1.0])
    s, c = np.linalg.norm(axis), n[2]
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s**2)


def relevel(room_points, room_poses, most_floor_tilt_deg=15.0):
    """The correction for a room that is already in a room frame but levelled wrongly.

    For rooms built before the floor fix of 18 Nov 2026. The floor is found
    as `level_room` now finds it, starting from the room frame's own z as
    "up". Returns a dict:

        R, floor_h      the correction, in the form points_to_room and
                        poses_to_room take: corrected = points_to_room(old, R, floor_h)
        up_from         "floor", or "cameras" when no floor plane was found
                        (then only the height is corrected)
        floor_tilt_deg  how far the floor was from level, in degrees (None
                        when no floor plane was found)
    """
    room_poses = np.asarray(room_poses, dtype=float)
    up = np.array([0.0, 0.0, 1.0])
    low, high, peak = floor_layer(room_points, up, room_poses[:, :3, 3])
    plane = floor_plane(room_points, up, low, high, most_tilt_deg=most_floor_tilt_deg)
    if plane is None:
        return {"R": np.eye(3), "floor_h": peak, "up_from": "cameras", "floor_tilt_deg": None}
    normal, height, tilt = plane
    return {"R": tilt_turn(normal), "floor_h": height, "up_from": "floor", "floor_tilt_deg": tilt}


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


def level_room(points, poses, voxel=0.02, least_consistency=0.8, align_walls=False, most_floor_tilt_deg=15.0):
    """The whole "level, thin, keep anchors" step.

    points: N x 3 from the model.  poses: F x 4 x 4, one per frame used.

    Which way is up: first from how the phone was held (`estimate_up`), then
    from the floor itself (`floor_height`, `floor_plane`). The phone's answer
    leans toward the way it faced most when it was tilted down; the floor's
    does not. The floor's answer is used unless it is more than
    `most_floor_tilt_deg` from the phone's, which no real floor is.

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
        up_from       "floor" or "cameras": which answer for up was used
        floor_tilt_deg  the angle between the floor's up and the phone's, in
                      degrees (None if no floor plane could be fitted)

    Raises Refilm when up cannot be trusted or the floor cannot be found.
    """
    points = np.asarray(points, dtype=float)
    poses = np.asarray(poses, dtype=float)
    up, consistency = estimate_up(poses)
    if consistency < least_consistency:
        raise Refilm("the phone tilted too much for the floor to be found; film again, held upright")
    low, high, floor_h = floor_layer(points, up, poses[:, :3, 3])
    plane = floor_plane(points, up, low, high, most_tilt_deg=most_floor_tilt_deg)
    up_from, floor_tilt = "cameras", None
    if plane is not None:
        up, floor_h, floor_tilt = plane
        up_from = "floor"
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
        "up_from": up_from,
        "floor_tilt_deg": floor_tilt,
    }
