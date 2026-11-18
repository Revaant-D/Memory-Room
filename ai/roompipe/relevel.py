"""Re-levelling a room folder that was levelled wrongly, without the GPU.

Rooms built before the floor fix of 18 Nov 2026 could take a bed top for
the floor, and leaned toward the way the phone faced most. The model's
output in such a room is fine; only the last move into the room frame is
wrong. This module finds the floor again (roomgeom.level.relevel) and moves
every room-frame number in the folder by the correction:

    points.ply / points.bin   the points
    room.json                 the anchors' poses, the box, the move from the
                              model's frame; and a "relevelled" record
    cameras.json              every frame's pose
    dense.npz                 the 3D point behind every pixel
    placements.json           each placed photo's spot and facing

Everything else (frames, anchors' pictures, run.json) is copied unchanged.
The source folder or zip is never changed: the result goes to a new folder.
Needs numpy only.
"""

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from roomgeom.level import points_to_room, poses_to_room, relevel, room_box
from roomgeom.pointsfile import READERS, WRITERS

from roompipe.build import CAMERAS_FILE, DENSE_FILE, ROOM_FILE
from roompipe.place import PLACEMENTS_FILE


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, data):
    Path(path).write_text(json.dumps(data, indent=1), encoding="utf-8")


def relevel_room_folder(source, out_dir):
    """Copy the room at `source` (a room folder or its zip) to `out_dir`, re-levelled.

    `out_dir` must be new or empty. Returns the new room.json as a dict.
    Raises ValueError when `out_dir` already holds files or `source` holds
    no room.
    """
    source, out_dir = Path(source), Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"{out_dir} already holds files; give a new or empty folder")
    if source.is_dir():
        if not (source / ROOM_FILE).is_file():
            raise ValueError(f"{source} holds no {ROOM_FILE}, so it is not a room folder")
        shutil.copytree(source, out_dir, dirs_exist_ok=True)
    elif source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            if ROOM_FILE not in archive.namelist():
                raise ValueError(f"{source} holds no {ROOM_FILE} at its top, so it is not a room zip")
            archive.extractall(out_dir)  # extractall keeps every file inside out_dir
    else:
        raise ValueError(f"{source} is neither a room folder nor a zip")

    room = _read(out_dir / ROOM_FILE)
    files = room["points_files"]
    kind = "ply" if "ply" in files else "bin"
    points, colors = READERS[kind](out_dir / files[kind])
    cameras = _read(out_dir / CAMERAS_FILE) if (out_dir / CAMERAS_FILE).is_file() else None
    poses = np.array([c["pose"] for c in (cameras["cameras"] if cameras else room["anchors"])], dtype=float)

    fix = relevel(points, poses)
    R, floor_h = fix["R"], fix["floor_h"]

    moved = points_to_room(points, R, floor_h)
    for each_kind, name in files.items():
        WRITERS[each_kind](out_dir / name, moved, colors)

    for anchor in room["anchors"]:
        anchor["pose"] = poses_to_room(np.array([anchor["pose"]]), R, floor_h)[0].tolist()
    if cameras:
        for camera in cameras["cameras"]:
            camera["pose"] = poses_to_room(np.array([camera["pose"]]), R, floor_h)[0].tolist()
        _write(out_dir / CAMERAS_FILE, cameras)

    if (out_dir / DENSE_FILE).is_file():
        with np.load(out_dir / DENSE_FILE) as dense:
            arrays = {key: dense[key] for key in dense.files}
        frames = arrays["points"]
        for i in range(len(frames)):  # one frame at a time, to keep memory small
            flat = frames[i].reshape(-1, 3).astype(float)
            frames[i] = points_to_room(flat, R, floor_h).reshape(frames[i].shape).astype(frames.dtype)
        np.savez_compressed(out_dir / DENSE_FILE, **arrays)

    if (out_dir / PLACEMENTS_FILE).is_file():
        placements = _read(out_dir / PLACEMENTS_FILE)
        for entry in placements:
            if entry.get("x") is not None:
                spot = points_to_room(np.array([[entry["x"], entry["y"], entry["z"]]]), R, floor_h)[0]
                entry["x"], entry["y"], entry["z"] = (float(v) for v in spot)
            if entry.get("facing") is not None:
                entry["facing"] = (R @ np.asarray(entry["facing"], dtype=float)).tolist()
        _write(out_dir / PLACEMENTS_FILE, placements)

    before = {"box": room["box"], "model_to_room": room["model_to_room"]}
    move = room["model_to_room"]  # room = model @ R.T - [origin_x, origin_y, floor_h]
    offset = np.array([*move["origin_xy"], move["floor_h"]]) @ R.T + [0.0, 0.0, floor_h]
    room["model_to_room"] = {
        "R": (R @ np.array(move["R"])).tolist(),
        "floor_h": float(offset[2]),
        "origin_xy": offset[:2].tolist(),
    }
    low, high = room_box(moved)
    room["box"] = {"low": low.tolist(), "high": high.tolist()}
    tilt = None if fix["floor_tilt_deg"] is None else round(float(fix["floor_tilt_deg"]), 3)
    room["up_from"], room["floor_tilt_deg"] = fix["up_from"], tilt
    room["relevelled"] = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "how": "python -m roompipe relevel (roomgeom.level.relevel), on the room's own points",
        "why": "built before the floor fix of 18 Nov 2026",
        "up_from": fix["up_from"],
        "floor_tilt_deg": tilt,
        "floor_was_at_m": round(float(floor_h), 4),  # the floor's height in the old frame
        "before": before,
    }
    _write(out_dir / ROOM_FILE, room)
    return room
