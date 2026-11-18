"""Reading and writing the room's points file, in the two candidate formats.

The format of the points file is an OPEN DECISION of the builder's
(docs/design/2026-11-16-first-draft.md, "Open questions"). Both candidates
are implemented here so that whichever is chosen is ready, and so the two
can be compared on a real room before choosing.

    "bin"   The layout sketched in the T5 technical design. No header.
            First every point's x, y, z as 32-bit floats, then every point's
            red, green, blue as single bytes. 15 bytes per point.
            A browser reads it in two lines. Nothing else can open it, and
            the file does not say what it is.

    "ply"   The standard PLY format, binary little-endian. A short text
            header, then per point: x, y, z as 32-bit floats and red, green,
            blue as single bytes. 15 bytes per point plus the header.
            Opens in MeshLab, CloudCompare and Blender, so a room can be
            looked at before any viewer exists. three.js ships a PLYLoader.

Points are in the room frame: metres, floor at z = 0, z up. Colours are
whole numbers 0 to 255.
"""

from pathlib import Path

import numpy as np

BYTES_PER_POINT = 15  # 3 floats of 4 bytes + 3 colour bytes, in both formats

_PLY_ROW = np.dtype(
    [("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")]
)
_PLY_HEADER = (
    "ply\n"
    "format binary_little_endian 1.0\n"
    "comment Memory Room: metres, floor at z = 0, z up\n"
    "element vertex {count}\n"
    "property float x\n"
    "property float y\n"
    "property float z\n"
    "property uchar red\n"
    "property uchar green\n"
    "property uchar blue\n"
    "end_header\n"
)


def _checked(points, colors):
    """Return (points as float32 N x 3, colours as uint8 N x 3), or raise ValueError."""
    points = np.asarray(points)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must be N x 3")
    if not np.isfinite(points).all():
        raise ValueError("points contain values that are not real numbers")
    if colors is None:
        colors = np.full((len(points), 3), 128, dtype=np.uint8)  # mid grey
    colors = np.asarray(colors)
    if colors.shape != points.shape:
        raise ValueError("colors must be N x 3, one row per point")
    if not np.issubdtype(colors.dtype, np.integer):
        raise ValueError("colors must be whole numbers 0 to 255 (not 0.0 to 1.0)")
    if colors.size and (colors.min() < 0 or colors.max() > 255):
        raise ValueError("colors must be between 0 and 255")
    return points.astype("<f4"), colors.astype(np.uint8)


def write_bin(path, points, colors=None):
    """Write the T5 layout: all positions, then all colours. Returns the number of points."""
    points, colors = _checked(points, colors)
    with open(path, "wb") as f:
        f.write(points.tobytes())
        f.write(colors.tobytes())
    return len(points)


def read_bin(path):
    """Read a file written by `write_bin`. Returns (points, colors)."""
    data = Path(path).read_bytes()
    if len(data) % BYTES_PER_POINT:
        raise ValueError("not a points file: its size is not a whole number of 15-byte points")
    n = len(data) // BYTES_PER_POINT
    points = np.frombuffer(data, dtype="<f4", count=n * 3).reshape(n, 3)
    colors = np.frombuffer(data, dtype=np.uint8, offset=n * 12).reshape(n, 3)
    return points.copy(), colors.copy()


def write_ply(path, points, colors=None):
    """Write a binary PLY that standard 3D tools can open. Returns the number of points."""
    points, colors = _checked(points, colors)
    rows = np.empty(len(points), dtype=_PLY_ROW)
    rows["x"], rows["y"], rows["z"] = points[:, 0], points[:, 1], points[:, 2]
    rows["red"], rows["green"], rows["blue"] = colors[:, 0], colors[:, 1], colors[:, 2]
    with open(path, "wb") as f:
        f.write(_PLY_HEADER.format(count=len(points)).encode("ascii"))
        f.write(rows.tobytes())
    return len(points)


def read_ply(path):
    """Read a PLY written by `write_ply`. Returns (points, colors).

    This is not a general PLY reader. It accepts exactly the layout
    `write_ply` produces (comment lines aside) and refuses anything else, so
    a file with a different layout fails loudly and is never misread.
    """
    data = Path(path).read_bytes()
    marker = b"end_header\n"
    end = data.find(marker)
    if not data.startswith(b"ply\n") or end < 0:
        raise ValueError("not a PLY file")
    lines = [
        line
        for line in data[:end].decode("ascii", errors="replace").split("\n")
        if line and not line.startswith("comment")
    ]
    wanted = [line for line in _PLY_HEADER.split("\n") if line and not line.startswith("comment")]
    wanted = wanted[:-1]  # all but "end_header", which was cut off above
    count = None
    for got, want in zip(lines, wanted, strict=False):
        if want.startswith("element vertex"):
            if not got.startswith("element vertex "):
                raise ValueError("this PLY does not have the layout Memory Room writes")
            count = int(got.split()[2])
        elif got != want:
            raise ValueError("this PLY does not have the layout Memory Room writes")
    if count is None or len(lines) != len(wanted):
        raise ValueError("this PLY does not have the layout Memory Room writes")
    body = data[end + len(marker) :]
    if len(body) != count * BYTES_PER_POINT:
        raise ValueError("this PLY is cut short or has extra data")
    rows = np.frombuffer(body, dtype=_PLY_ROW)
    points = np.column_stack([rows["x"], rows["y"], rows["z"]])
    colors = np.column_stack([rows["red"], rows["green"], rows["blue"]])
    return points, colors


WRITERS = {"bin": write_bin, "ply": write_ply}
READERS = {"bin": read_bin, "ply": read_ply}
