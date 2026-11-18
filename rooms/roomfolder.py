"""Reading a room built by the Colab notebook (ai/build_room_colab.ipynb).

A room arrives as a folder, or as the zip the notebook writes beside it. This
module finds the room inside, reads its room.json and run.json, and checks
that points.ply has exactly the layout the AI code writes
(ai/roomgeom/pointsfile.py), so the viewer is never handed a file it would
misread. It also decides whether the room is a MADE-UP ROOM (made by the
stand-in model) and whether it came from the allowed weights.

Only Python's standard library is used: numpy is not in the app's environment.
`manage.py import_room` is the one caller.
"""

import json
import zipfile
from contextlib import contextmanager
from pathlib import Path

ROOM_FILE = "room.json"
RUN_FILE = "run.json"
POINTS_FILE = "points.ply"
ROOM_VERSION = 1
# The only weights a real room may come from (project rule: Apache-2.0 only).
ALLOWED_MODEL = "facebook/map-anything-apache"

# The PLY header the AI code writes, without its comment line. "element vertex"
# carries the point count and is checked separately.
_PLY_LINES = [
    "ply",
    "format binary_little_endian 1.0",
    "element vertex",
    "property float x",
    "property float y",
    "property float z",
    "property uchar red",
    "property uchar green",
    "property uchar blue",
]
_END = b"end_header\n"
BYTES_PER_POINT = 15  # three 4-byte floats and three colour bytes
_HEADER_LIMIT = 4096  # the real header is about 250 bytes


class RoomError(Exception):
    """A room that cannot be imported. The message says why, in plain words."""


# --- Where the files are: a folder or a zip ----------------------------------


class _FolderRoom:
    def __init__(self, base):
        self.base = base

    def has(self, name):
        return (self.base / name).is_file()

    def size(self, name):
        return (self.base / name).stat().st_size

    def open(self, name):
        return open(self.base / name, "rb")


class _ZipRoom:
    def __init__(self, archive, prefix):
        self.archive, self.prefix = archive, prefix
        self.names = set(archive.namelist())

    def has(self, name):
        return self.prefix + name in self.names

    def size(self, name):
        return self.archive.getinfo(self.prefix + name).file_size

    def open(self, name):
        return self.archive.open(self.prefix + name)


def _room_places(names):
    """The folders (as prefixes, "" for the top) that hold a room.json or run.json."""
    places = set()
    for name in names:
        parts = name.split("/")
        if parts[-1] in (ROOM_FILE, RUN_FILE) and len(parts) <= 2:
            places.add("" if len(parts) == 1 else parts[0] + "/")
    return places


def _one_place(places, where):
    if "" in places:
        return ""
    if len(places) > 1:
        raise RoomError(f"{where} holds {len(places)} rooms; give the path of one of them.")
    return places.pop() if places else ""


@contextmanager
def open_room(path):
    """Yield the room at `path`: a room folder, a folder holding one, or a zip of either."""
    path = Path(path)
    if path.is_dir():
        inner = [child.name + "/" + file for child in path.iterdir() if child.is_dir()
                 for file in (ROOM_FILE, RUN_FILE) if (child / file).is_file()]
        top = [file for file in (ROOM_FILE, RUN_FILE) if (path / file).is_file()]
        prefix = _one_place(_room_places(top + inner), path.name)
        yield _FolderRoom(path / prefix if prefix else path)
    elif path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            # Only these named files are ever read from the zip; nothing is
            # unpacked, so a strange path inside it cannot write anywhere.
            yield _ZipRoom(archive, _one_place(_room_places(archive.namelist()), path.name))
    elif path.exists():
        raise RoomError(f"{path} is neither a folder nor a zip file.")
    else:
        raise RoomError(f"There is nothing at {path}.")


# --- What the files say --------------------------------------------------------


def _read_json(room, name):
    try:
        with room.open(name) as file:
            data = json.loads(file.read().decode("utf-8"))
    except (ValueError, UnicodeError) as problem:
        raise RoomError(f"{name} is not readable JSON: {problem}") from problem
    if not isinstance(data, dict):
        raise RoomError(f"{name} does not hold the facts it should.")
    return data


def _header_line_ok(got, want):
    if want == "element vertex":
        return got.startswith("element vertex ")
    return got == want


def ply_point_count(room):
    """Check points.ply's layout and length; return its number of points."""
    with room.open(POINTS_FILE) as file:
        head = file.read(_HEADER_LIMIT)
    end = head.find(_END)
    if not head.startswith(b"ply\n") or end < 0:
        raise RoomError(f"{POINTS_FILE} is not a PLY file.")
    lines = [line for line in head[:end].decode("ascii", errors="replace").split("\n")
             if line and not line.startswith("comment")]
    count = None
    if len(lines) == len(_PLY_LINES) and all(map(_header_line_ok, lines, _PLY_LINES)):
        text = lines[_PLY_LINES.index("element vertex")].split(" ", 2)[2]
        count = int(text) if text.isdigit() else None
    if count is None:
        raise RoomError(f"{POINTS_FILE} does not have the layout Memory Room writes "
                        "(x, y, z as floats, then red, green, blue).")
    expected = end + len(_END) + count * BYTES_PER_POINT
    actual = room.size(POINTS_FILE)
    if actual < expected:
        raise RoomError(f"{POINTS_FILE} is cut short: its header promises {count:,} points, "
                        f"which needs {expected:,} bytes, but the file has {actual:,}.")
    if actual > expected:
        raise RoomError(f"{POINTS_FILE} does not have the layout Memory Room writes: "
                        f"it has {actual - expected:,} bytes after its {count:,} points.")
    return count


def _is_stand_in(model_id):
    # The stand-in model's two labels: "MADE-UP ROOM: stand-in model, ..." in
    # run.json and "stand-in (made-up room, ...)" in room.json.
    return "stand-in" in str(model_id or "")


def _same_model(a, b):
    if _is_stand_in(a) or _is_stand_in(b):
        return _is_stand_in(a) and _is_stand_in(b)
    return a == b


def check_room(room, made_up_allowed=False):
    """Read and check a room. Returns the facts to keep on the scan (Scan.room_info).

    Raises RoomError, with the reason, for anything that should not reach the app.
    """
    run = _read_json(room, RUN_FILE) if room.has(RUN_FILE) else {}
    if not room.has(ROOM_FILE):
        why = run.get("stopped_because")
        raise RoomError(f"There is no {ROOM_FILE} here, so the run did not build a room."
                        + (f" {RUN_FILE} says it stopped because {why}" if why else ""))
    if run.get("finished") is False:
        # A rerun that failed early can leave an earlier run's room files beside
        # its own run.json; they must not be taken for this run's room.
        why = run.get("stopped_because")
        raise RoomError(f"{RUN_FILE} says this run did not finish"
                        + (f": it stopped because {why}" if why else "")
                        + ". Any room files beside it are from another run.")
    facts = _read_json(room, ROOM_FILE)
    if facts.get("version") != ROOM_VERSION:
        raise RoomError(f"{ROOM_FILE} is version {facts.get('version')}; "
                        f"this app reads version {ROOM_VERSION}.")
    if not room.has(POINTS_FILE):
        raise RoomError(f"The room has no {POINTS_FILE}; the viewer needs it.")
    count = ply_point_count(room)
    if facts.get("n_points") != count:
        raise RoomError(f"{ROOM_FILE} says {facts.get('n_points')} points, "
                        f"but {POINTS_FILE} holds {count:,}.")

    model = facts.get("model_info") if isinstance(facts.get("model_info"), dict) else {}
    run_model, room_model = run.get("model_id"), model.get("model_id")
    if run_model and room_model and not _same_model(run_model, room_model):
        raise RoomError(f"{RUN_FILE} and {ROOM_FILE} disagree on which model made this room "
                        f"({run_model}; {room_model}), so they are from different runs.")
    model_id = run_model or room_model
    made_up = run.get("stand_in") is True or _is_stand_in(run_model) or _is_stand_in(room_model)
    if made_up and not made_up_allowed:
        raise RoomError("This is a MADE-UP ROOM, made by the stand-in model, not a reconstruction. "
                        "To import it anyway, labelled as made up, add --made-up.")
    if not made_up:
        if made_up_allowed:
            raise RoomError(f"--made-up was given, but this room was made by {model_id}, "
                            "not the stand-in model. Leave out --made-up.")
        if not model_id:
            raise RoomError(f"Can't tell which model made this room: neither {RUN_FILE} "
                            f"nor {ROOM_FILE} names one.")
        if model_id != ALLOWED_MODEL:
            raise RoomError(f"This room was made by {model_id}. Only rooms made with "
                            f"{ALLOWED_MODEL} (Apache-2.0 weights) may be imported.")

    return {
        "n_points": count,
        "box": facts.get("box"),
        "up_consistency": facts.get("up_consistency"),
        "frames_used": facts.get("frames_used"),
        "has_colors": facts.get("has_colors"),
        "wall_aligned": facts.get("wall_aligned"),
        "voxel_m": facts.get("voxel_m"),
        "model_id": model_id,
        "weights_revision": run.get("weights_revision") or model.get("weights_revision"),
        "precision": run.get("precision_used") or model.get("precision"),
        "gpu": run.get("gpu"),
        "run_name": run.get("run_name"),
        "made_up": made_up,
    }
