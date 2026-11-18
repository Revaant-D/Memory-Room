"""Placing photos in a built room: room folder + photos -> model -> pin or ask.

For each batch of photos the model runs twice, once with the even-numbered
anchors and once with the odd-numbered ones. Each run gives every photo a
position; roomgeom.place decides whether the two agree well enough to pin.

The result for each photo matches the app's Pin model on purpose:

    placed_by "ai"   -> make Pin(memory, scan, x, y, z, placed_by="ai")
    placed_by None   -> do not pin; show `reason` and let the person tap the spot

Nothing here writes to Django. Turning these results into Pin rows needs a
way to tell which Memory each photo file is, which is not decided.
"""

import json
import math
from pathlib import Path

import numpy as np
from roomgeom.place import Thresholds, check_two_tries, place_from_poses, split_anchors

from roompipe.build import load_room

PLACEMENTS_FILE = "placements.json"
PHOTOS_PER_PASS = 10  # the design: "up to about 10 of your photos" with the anchors


def _numbers(values):
    """A list of floats for JSON, or None if any is not a real number."""
    values = [float(v) for v in values]
    return values if all(math.isfinite(v) for v in values) else None


def place_photos(room_dir, photo_paths, run_model, thresholds=Thresholds(), save=True):
    """Place photos in the room. Returns one dict per photo, in the order given.

    Each dict: photo (file name), placed_by ("ai" or None), reason, x, y, z
    (metres in the room frame, or None), facing (unit vector or None),
    gap_m, turn_deg, anchor_residual_m.

    With save=True the list is also written to placements.json in the room folder.
    """
    room_dir = Path(room_dir)
    room = load_room(room_dir)
    anchors = room["anchors"]
    if len(anchors) < 6:
        raise ValueError(f"the room has {len(anchors)} anchors; two tries need at least 6")
    anchor_paths = [room_dir / a["file"] for a in anchors]
    anchor_poses = np.array([a["pose"] for a in anchors], dtype=float)
    box = (np.array(room["box"]["low"]), np.array(room["box"]["high"]))
    halves = split_anchors(len(anchors))

    photo_paths = [Path(p) for p in photo_paths]
    results = []
    for start in range(0, len(photo_paths), PHOTOS_PER_PASS):
        batch = photo_paths[start : start + PHOTOS_PER_PASS]
        # The model runs outside the `try` below: a pass that fails (fp16 giving
        # values that are not real numbers, an image the loader skipped) stops
        # here, so it is recorded as a failure and never mistaken for photos the
        # model was honestly unsure about.
        outputs = [run_model([anchor_paths[i] for i in half] + batch) for half in halves]
        try:
            tries = [place_from_poses(output.poses, anchor_poses[half])
                     for output, half in zip(outputs, halves, strict=True)]
            (try_a, residual_a), (try_b, residual_b) = tries
            checked = check_two_tries(try_a, residual_a, try_b, residual_b, box, thresholds)
            residual = max(residual_a, residual_b)
        except ValueError as problem:
            # The anchors could not support a fit. Nothing in this batch is pinned.
            checked = [
                {"pos": [math.nan] * 3, "facing": [math.nan] * 3, "gap_m": math.nan,
                 "turn_deg": math.nan, "placed_by": None, "reason": str(problem)}
                for _ in batch
            ]
            residual = math.nan

        for path, result in zip(batch, checked, strict=True):
            position = _numbers(result["pos"])
            x, y, z = position if position else (None, None, None)
            results.append(
                {
                    "photo": path.name,
                    "placed_by": result["placed_by"],
                    "reason": result["reason"],
                    "x": x,
                    "y": y,
                    "z": z,
                    "facing": _numbers(result["facing"]),
                    "gap_m": (_numbers([result["gap_m"]]) or [None])[0],
                    "turn_deg": (_numbers([result["turn_deg"]]) or [None])[0],
                    "anchor_residual_m": (_numbers([residual]) or [None])[0],
                }
            )

    if save:
        (room_dir / PLACEMENTS_FILE).write_text(json.dumps(results, indent=1), encoding="utf-8")
    return results


def summary_lines(results):
    """A plain-text table of the results, for a notebook or a terminal."""
    lines = [f"{'photo':<28} {'result':<8} {'x':>6} {'y':>6} {'z':>6}  {'gap m':>6} {'turn':>5}  note"]
    for r in results:
        where = [f"{r[k]:6.2f}" if r[k] is not None else "     -" for k in ("x", "y", "z")]
        gap = f"{r['gap_m']:6.2f}" if r["gap_m"] is not None else "     -"
        turn = f"{r['turn_deg']:5.0f}" if r["turn_deg"] is not None else "    -"
        verdict = "pinned" if r["placed_by"] == "ai" else "ask"
        lines.append(f"{r['photo'][:28]:<28} {verdict:<8} {' '.join(where)}  {gap} {turn}  {r['reason']}")
    pinned = sum(r["placed_by"] == "ai" for r in results)
    lines.append(f"{pinned} of {len(results)} pinned; the rest need the person to place them.")
    return lines
