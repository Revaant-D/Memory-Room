"""Building a room: frames -> model -> a folder on disk that holds the room.

The folder ("room folder") is everything later steps need:

    room.json        facts about the room, each anchor's file and pose, and the
                     move from the model's frame into the room frame
    points.bin       the thinned, levelled, coloured points (T5 layout)
    points.ply       the same points as a standard PLY
    anchors/         copies of the frames kept as anchors (about 20)

When the model hands back its per-image detail (ModelOutput.views), three
more things are written, so that a different way of placing photos can be
tried later without running the model again:

    frames/          every frame, exactly as the model saw it (resized, cropped)
    cameras.json     every frame's camera: pose in the room frame, and intrinsics
    dense.npz        for every frame, the 3D point behind each pixel (room frame),
                     the model's confidence, and which pixels are valid

Both point files are written until the builder chooses a format; pass
formats=("ply",) or ("bin",) to write one.

How the room folder reaches Django (which fields land on Scan, where the
anchors are stored) is not decided and is not done here.
"""

import json
import shutil
from pathlib import Path

import numpy as np
from roomgeom.level import level_room, points_to_room
from roomgeom.pointsfile import WRITERS

ROOM_FILE = "room.json"
CAMERAS_FILE = "cameras.json"
DENSE_FILE = "dense.npz"

# Written into cameras.json so nobody has to guess what the numbers mean.
POSE_CONVENTION = (
    "4 x 4 camera-to-room matrices. Camera axes as OpenCV: +x right, +y down, +z forward. "
    "Room: metres, floor at z = 0, z up. Intrinsics are for the frame image in frames/."
)


def build_room(frame_paths, run_model, out_dir, voxel=0.02, align_walls=False, formats=("bin", "ply")):
    """Make a room folder from frames. Returns the dict written to room.json.

    frame_paths: the frames, in the order they were filmed.
    run_model:   a function (list of image paths) -> ModelOutput; see roompipe.model.
    align_walls: see roomgeom.level.wall_aligned_turn. Off by default, which
                 is the technical design as written.

    Raises roomgeom.level.Refilm when the video cannot be levelled.
    """
    frame_paths = [Path(p) for p in frame_paths]
    output = run_model(frame_paths)
    if len(output.poses) != len(frame_paths):
        raise ValueError(
            f"the model returned {len(output.poses)} poses for {len(frame_paths)} frames"
        )

    level = level_room(output.points, output.poses, voxel=voxel, align_walls=align_walls)
    points = level["room_points"]
    colors = None if output.colors is None else output.colors[level["keep"]]

    out_dir = Path(out_dir)
    (out_dir / "anchors").mkdir(parents=True, exist_ok=True)
    points_files = {}
    for kind in formats:
        WRITERS[kind](out_dir / f"points.{kind}", points, colors)
        points_files[kind] = f"points.{kind}"

    anchors = []
    for index in level["anchors"]:
        source = frame_paths[index]
        # The anchor keeps its frame's name, so it can be traced back to the video.
        shutil.copyfile(source, out_dir / "anchors" / source.name)
        anchors.append(
            {
                "file": f"anchors/{source.name}",
                "frame": index,
                "pose": level["room_poses"][index].tolist(),  # 4 x 4, camera-to-room
            }
        )

    bundle = {}
    if output.views is not None:
        bundle = write_views(out_dir, frame_paths, output.views, level)

    low, high = level["box"]
    room = {
        "version": 1,
        "frames_used": len(frame_paths),
        "n_points": int(len(points)),
        "has_colors": colors is not None,
        "box": {"low": low.tolist(), "high": high.tolist()},  # metres; floor is z = 0
        "up_consistency": round(float(level["consistency"]), 4),
        # Which way is up came from the floor's own plane, or from the phone when no floor plane was found.
        "up_from": level["up_from"],
        "floor_tilt_deg": None if level["floor_tilt_deg"] is None else round(float(level["floor_tilt_deg"]), 3),
        "wall_aligned": bool(align_walls),
        "voxel_m": voxel,
        "points_files": points_files,
        "anchors": anchors,
        # room = (model point) @ R.T, then z -= floor_h, then x, y -= origin_xy
        "model_to_room": {
            "R": np.asarray(level["R"]).tolist(),
            "floor_h": float(level["floor_h"]),
            "origin_xy": np.asarray(level["origin_xy"], dtype=float).tolist(),
        },
        "bundle": bundle,
        "model_info": output.info or {},
    }
    (out_dir / ROOM_FILE).write_text(json.dumps(room, indent=1), encoding="utf-8")
    return room


def write_views(out_dir, frame_paths, views, level):
    """Write frames/, cameras.json and dense.npz. Returns their names for room.json."""
    from PIL import Image

    if len(views) != len(frame_paths):
        raise ValueError(f"the model returned detail for {len(views)} of {len(frame_paths)} frames")
    height, width = views[0]["points"].shape[:2]
    if any(v["points"].shape[:2] != (height, width) for v in views):
        raise ValueError("the model's frames are not all the same size")

    out_dir = Path(out_dir)
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)
    count = len(views)
    dense_points = np.empty((count, height, width, 3), dtype=np.float16)
    dense_conf = np.empty((count, height, width), dtype=np.float16)
    dense_mask = np.empty((count, height, width), dtype=bool)
    cameras = []
    for i, (source, view) in enumerate(zip(frame_paths, views, strict=True)):
        name = f"frames/{source.stem}.jpg"
        Image.fromarray(np.asarray(view["image"], dtype=np.uint8)).save(out_dir / name, quality=92)
        in_room = points_to_room(np.asarray(view["points"]).reshape(-1, 3), level["R"], level["floor_h"],
                                 level["origin_xy"])
        dense_points[i] = in_room.reshape(height, width, 3)
        dense_conf[i] = view["conf"]
        dense_mask[i] = view["mask"]
        intrinsics = view.get("intrinsics")
        cameras.append({
            "frame": i,
            "file": name,
            "source": source.name,
            "pose": level["room_poses"][i].tolist(),
            "intrinsics": None if intrinsics is None else np.asarray(intrinsics, dtype=float).tolist(),
        })
    np.savez_compressed(out_dir / DENSE_FILE, points=dense_points, conf=dense_conf, mask=dense_mask)
    (out_dir / CAMERAS_FILE).write_text(
        json.dumps({"convention": POSE_CONVENTION, "width": int(width), "height": int(height),
                    "cameras": cameras}, indent=1),
        encoding="utf-8",
    )
    return {"frames": "frames/", "cameras": CAMERAS_FILE, "dense": DENSE_FILE}


def load_room(room_dir):
    """Read room.json from a room folder."""
    return json.loads((Path(room_dir) / ROOM_FILE).read_text(encoding="utf-8"))
