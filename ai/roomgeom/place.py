"""Placing a photo in a stored room, and deciding whether to trust the answer.

The plan from the T5 technical design ("Placing a photo, and knowing when
not to"):

1. Run the model once over some of the room's anchor frames PLUS the new
   photos. It returns a camera pose for every image, in a frame of its own.
2. The anchors' positions are known in the room frame. Fit the model's frame
   onto the room frame using them (roomgeom.fit.umeyama).
3. Apply the same fit to the photos' poses. That is where each photo was
   taken, in the room.
4. Do it twice, with two different halves of the anchors. Pin the photo only
   if the two answers agree and the spot is inside the room. Otherwise ask
   the person.

This module is steps 2 to 4. Step 1 is the model call, which lives elsewhere
and has never been run; this module takes its output as plain arrays.

Status: the maths below is tested on made-up data with known answers. It has
NOT been tested on real model output. The four thresholds are the design's
starting guesses, to be set by the ten-photo test.
"""

from dataclasses import dataclass

import numpy as np

from roomgeom.fit import apply_fit, fit_residuals, on_a_line, umeyama


@dataclass(frozen=True)
class Thresholds:
    """When to pin a photo without asking. All four are starting guesses."""

    anchor_residual_m: float = 0.15  # the anchors must line up at least this well
    gap_m: float = 0.7  # the two tries must agree on position within this (arm's length)
    turn_deg: float = 30.0  # ... and on which way the camera faced within this
    box_margin_m: float = 0.3  # the spot may be this far outside the room's box


def split_anchors(n_anchors):
    """The two halves used for the two tries: even-numbered and odd-numbered anchors."""
    return list(range(0, n_anchors, 2)), list(range(1, n_anchors, 2))


def place_from_poses(run_poses, anchor_room_poses):
    """Steps 2 and 3 for one model pass.

    run_poses:          (A + P) x 4 x 4, the model's poses for A anchors
                        followed by P photos, in the model's own frame.
    anchor_room_poses:  A x 4 x 4, the same A anchors' stored poses in the
                        room frame, in the same order.

    Returns (found, residual):
        found     one (position, facing) pair per photo. position is x, y, z
                  in metres in the room frame; facing is a unit vector, the
                  direction the camera looked.
        residual  the worst distance, in metres, between an anchor's fitted
                  position and its stored one. Small means the fit is good.

    Raises ValueError if the anchors cannot support a fit (too few, or all
    on one line).
    """
    run_poses = np.asarray(run_poses, dtype=float)
    anchor_room_poses = np.asarray(anchor_room_poses, dtype=float)
    n = len(anchor_room_poses)
    new_centres = run_poses[:n, :3, 3]
    old_centres = anchor_room_poses[:, :3, 3]
    if on_a_line(old_centres):
        raise ValueError("the anchors stand almost on one line; a fit from them would be a guess")

    s, R, t = umeyama(new_centres, old_centres)
    residual = float(fit_residuals(s, R, t, new_centres, old_centres).max())

    found = []
    for pose in run_poses[n:]:
        position = apply_fit(s, R, t, pose[:3, 3])
        facing = R @ pose[:3, 2]  # +Z is "forward" for the camera
        found.append((position, facing / np.linalg.norm(facing)))
    return found, residual


def inside(point, box, margin=0.0):
    """Is the point within the room's box, allowing `margin` metres outside it?"""
    low, high = box
    point = np.asarray(point, dtype=float)
    return bool(np.all(point >= np.asarray(low) - margin) and np.all(point <= np.asarray(high) + margin))


def check_two_tries(try_a, residual_a, try_b, residual_b, box, thresholds=Thresholds()):
    """Step 4: compare two tries and decide, photo by photo, whether to pin.

    try_a, try_b: the `found` lists from two calls of `place_from_poses`
    made with different anchors, for the same photos in the same order.

    Returns one dict per photo:
        pos        x, y, z: the middle of the two answers
        facing     unit vector from the first try
        gap_m      metres between the two answers
        turn_deg   degrees between the two facing directions
        placed_by  "ai" if every check passed, otherwise None
                   (None means: do not pin; ask the person)
        reason     "" when pinned, otherwise a short plain sentence saying
                   which check failed, for logs and for the person
    """
    worst_residual = max(residual_a, residual_b)
    results = []
    for (pos_a, face_a), (pos_b, face_b) in zip(try_a, try_b, strict=True):
        gap = float(np.linalg.norm(pos_a - pos_b))
        turn = float(np.degrees(np.arccos(np.clip(face_a @ face_b, -1.0, 1.0))))
        position = (pos_a + pos_b) / 2

        if not np.isfinite([gap, turn, worst_residual, *position]).all():
            reason = "the model's answer was not a real position"
        elif worst_residual >= thresholds.anchor_residual_m:
            reason = f"the room's anchors lined up only to within {worst_residual:.2f} m"
        elif gap >= thresholds.gap_m:
            reason = f"two tries {gap:.1f} m apart"
        elif turn >= thresholds.turn_deg:
            reason = f"two tries faced {turn:.0f} degrees apart"
        elif not inside(pos_a, box, thresholds.box_margin_m):
            reason = "the spot is outside the room"
        else:
            reason = ""

        results.append(
            {
                "pos": position,
                "facing": face_a,
                "gap_m": gap,
                "turn_deg": turn,
                "placed_by": None if reason else "ai",
                "reason": reason,
            }
        )
    return results
