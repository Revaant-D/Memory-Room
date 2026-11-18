"""Building a room: frames -> model -> a folder on disk that holds the room.

The folder ("room folder") is everything later steps need, and nothing else:

    room.json        facts about the room, and each anchor's file and pose
    points.bin       the thinned, levelled, coloured points (T5 layout)
    points.ply       the same points as a standard PLY
    anchors/         copies of the frames kept as anchors (about 20)

Both point files are written until the builder chooses a format; pass
formats=("ply",) or ("bin",) to write one.

The room folder is this component's own hand-off format. How it reaches
Django (which fields land on Scan, where the anchors are stored) is not
decided and is not done here.
"""

import json
import shutil
from pathlib import Path

from roomgeom.level import level_room
from roomgeom.pointsfile import WRITERS

ROOM_FILE = "room.json"


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

    low, high = level["box"]
    room = {
        "version": 1,
        "frames_used": len(frame_paths),
        "n_points": int(len(points)),
        "has_colors": colors is not None,
        "box": {"low": low.tolist(), "high": high.tolist()},  # metres; floor is z = 0
        "up_consistency": round(float(level["consistency"]), 4),
        "wall_aligned": bool(align_walls),
        "voxel_m": voxel,
        "points_files": points_files,
        "anchors": anchors,
    }
    (out_dir / ROOM_FILE).write_text(json.dumps(room, indent=1), encoding="utf-8")
    return room


def load_room(room_dir):
    """Read room.json from a room folder."""
    return json.loads((Path(room_dir) / ROOM_FILE).read_text(encoding="utf-8"))
