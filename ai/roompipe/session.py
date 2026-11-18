"""Helpers for the Colab notebook (ai/build_room_colab.ipynb).

The notebook's cells stay short and readable; the logic they need lives here,
where it is tested on this laptop with the stand-in model:

    RunLog               times each step, notes GPU memory, and is saved as run.json
    video_facts          length, frame rate and size of the room video
    pick_evenly          an even subset of frames (60 -> 40 -> 30 when memory runs out)
    build_with_fallback  build_room, retried with fewer frames if the GPU runs out of memory
    prepare_photos       photos -> upright JPEGs the model can read, GPS and other EXIF dropped
    rehearsal_model      the stand-in model wired to real file names, for a dry run
    frames_sheet, preview_png
                         pictures for a person to check by eye
    room_summary         the numbers a person should look at, in plain words

Nothing here imports torch or mapanything, so all of it runs without a GPU.
"""

import json
import platform
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from roompipe.build import build_room, load_room

RUN_FILE = "run.json"
PHOTO_ENDINGS = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp")
VIDEO_ENDINGS = (".mp4", ".mov", ".m4v")
STAND_IN_LABEL = "MADE-UP ROOM: stand-in model, not a reconstruction"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class RunLog:
    """Everything worth writing down about one run, saved as run.json.

    peak_memory: a function returning the GPU's peak memory in bytes since the
    last reset, and reset_memory: a function that resets it. In Colab these are
    torch.cuda.max_memory_allocated and torch.cuda.reset_peak_memory_stats.
    """

    def __init__(self, peak_memory=None, reset_memory=None, **facts):
        self.peak_memory, self.reset_memory = peak_memory, reset_memory
        self.data = {"started": now(), "python": platform.python_version(), **facts,
                     "steps": {}, "problems": []}

    @contextmanager
    def step(self, name):
        """Time a step. A failure is written down and then raised again."""
        if self.reset_memory:
            self.reset_memory()
        record = {"started": now()}
        self.data["steps"][name] = record
        start = time.perf_counter()
        try:
            yield record
            record["ok"] = True
        except BaseException as problem:
            record["ok"] = False
            record["error"] = f"{type(problem).__name__}: {problem}"[:2000]
            raise
        finally:
            record["seconds"] = round(time.perf_counter() - start, 2)
            if self.peak_memory:
                record["peak_gpu_gb"] = round(self.peak_memory() / 1e9, 2)

    def wrap_model(self, run_model, purpose):
        """The same model, with every call's image count, seconds and outcome written down.

        GPU memory is read after each call without resetting it, so a call's
        figure is the peak since its step began.
        """
        calls = self.data.setdefault("model_calls", [])

        def run(image_paths):
            record = {"purpose": purpose, "images": len(image_paths)}
            calls.append(record)
            start = time.perf_counter()
            try:
                output = run_model(image_paths)
                record["ok"] = True
                return output
            except BaseException as problem:
                record["ok"] = False
                record["error"] = f"{type(problem).__name__}: {problem}"[:300]
                raise
            finally:
                record["seconds"] = round(time.perf_counter() - start, 2)
                if self.peak_memory:
                    record["peak_gpu_gb"] = round(self.peak_memory() / 1e9, 2)

        return run

    def note(self, **facts):
        self.data.update(facts)

    def problem(self, text):
        self.data["problems"].append(text)

    def save(self, folder):
        self.data["saved"] = now()
        path = Path(folder) / RUN_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data, indent=1, default=str), encoding="utf-8")
        return path

    def table(self):
        """The steps as plain text: name, seconds, peak GPU memory, ok."""
        lines = [f"{'step':<22} {'seconds':>8} {'GPU GB':>7}  result"]
        for name, r in self.data["steps"].items():
            gb = f"{r['peak_gpu_gb']:7.2f}" if "peak_gpu_gb" in r else "      -"
            result = "ok" if r.get("ok") else r.get("error", "did not finish")[:60]
            lines.append(f"{name:<22} {r.get('seconds', 0):8.1f} {gb}  {result}")
        return "\n".join(lines)


def find_files(folder, endings):
    """Files in a folder with one of the endings (any case), newest first."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    found = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in endings]
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def video_facts(video):
    """Length, frame rate, frame count and stored size of a video, read with opencv."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f"cannot open video {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    facts = {
        "file": Path(video).name,
        "megabytes": round(Path(video).stat().st_size / 1e6, 1),
        "frames": frames,
        "fps": round(fps, 2),
        "seconds": round(frames / fps, 1) if fps else None,
        "stored_size": [int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))],
    }
    cap.release()
    return facts


def pick_evenly(items, n):
    """n items spread evenly from first to last, in order. All of them if n >= len(items)."""
    items = list(items)
    if n >= len(items):
        return items
    if n <= 0:
        return []
    indices = np.unique(np.linspace(0, len(items) - 1, n).round().astype(int))
    return [items[i] for i in indices]


def is_out_of_memory(problem):
    """True for a GPU out-of-memory error, recognised without importing torch."""
    text = f"{type(problem).__name__} {problem}".lower()
    return "outofmemory" in text.replace(" ", "") or "out of memory" in text


def build_with_fallback(frames, run_model, out_dir, tries=(60, 40, 30), after_failure=None, **build_args):
    """build_room, retried with fewer frames when the GPU runs out of memory.

    Returns (room, attempts). Each attempt is {"frames": n, "ok": bool, "error": text}.
    Any other error is raised at once: only running out of memory is retried.
    after_failure: called after an out-of-memory failure, before the next try
    (in Colab: free the GPU's cache).
    """
    attempts = []
    sizes = []
    for n in tries:
        n = min(n, len(frames))
        if n not in sizes:
            sizes.append(n)
    for n in sizes:
        out_dir = Path(out_dir)
        if out_dir.exists():
            shutil.rmtree(out_dir)  # nothing from a failed try may be mistaken for this one
        try:
            room = build_room(pick_evenly(frames, n), run_model, out_dir, **build_args)
        except Exception as problem:
            if not is_out_of_memory(problem):
                attempts.append({"frames": n, "ok": False, "error": f"{type(problem).__name__}: {problem}"[:500]})
                raise
            attempts.append({"frames": n, "ok": False, "error": "GPU out of memory"})
            if after_failure:
                after_failure()
            continue
        attempts.append({"frames": n, "ok": True})
        return room, attempts
    raise MemoryError(f"the GPU ran out of memory even with {sizes[-1]} frames: {attempts}")


def _register_heif():
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
        return True
    except ImportError:
        return False


def prepare_photos(photo_paths, out_dir, max_side=2048):
    """Copy photos as upright RGB JPEGs the model can read. Returns one dict per photo.

    The copies carry no EXIF at all, so a photo's GPS position never leaves this
    step. What placement may need from the EXIF (the date, the focal length) is
    read first and returned. HEIC needs pillow-heif; without it a HEIC photo is
    reported as skipped, not silently dropped.
    """
    from PIL import Image, ImageOps

    heif = _register_heif()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results, used_names = [], set()
    for source in sorted(Path(p) for p in photo_paths):
        entry = {"photo": source.name}
        try:
            with Image.open(source) as image:
                exif = image.getexif()
                details = exif.get_ifd(0x8769) if exif else {}
                entry["taken"] = details.get(0x9003) or exif.get(0x0132)  # DateTimeOriginal, DateTime
                focal_35 = details.get(0xA405)  # FocalLengthIn35mmFilm
                entry["focal_35mm"] = float(focal_35) if focal_35 else None
                upright = ImageOps.exif_transpose(image).convert("RGB")
            upright.thumbnail((max_side, max_side))
            width, height = upright.size
            name = f"{source.stem}.jpg"
            while name.lower() in used_names:
                name = f"{Path(name).stem}-2.jpg"
            used_names.add(name.lower())
            upright.save(out_dir / name, "JPEG", quality=95)
            entry.update(file=name, size=[width, height], shape="portrait" if height > width else "landscape")
        except Exception as problem:
            hint = " (HEIC needs pillow-heif)" if source.suffix.lower() in (".heic", ".heif") and not heif else ""
            entry.update(file=None, skipped=f"{type(problem).__name__}: {problem}{hint}"[:300])
        results.append(entry)
    return results


def rehearsal_model(frame_names, photo_names=(), view_size=(98, 56), seed=7):
    """The stand-in model, told where every one of these files was 'taken'.

    For a dry run of the notebook without a GPU. The frames get the stand-in's
    walk around a made-up bedroom; the photos get the made-up photo spots in
    turn. Everything it produces is a MADE-UP ROOM and must be labelled so.
    """
    from roompipe.fake import DEMO_PHOTOS, FakeRoomModel, camera, demo_room, walk_around

    points, colors = demo_room(spacing=0.05, seed=seed)
    truth = {name: pose for name, pose in zip(frame_names, walk_around(len(frame_names)), strict=True)}
    spots = list(DEMO_PHOTOS.values())
    for i, name in enumerate(photo_names):
        position, forward = spots[i % len(spots)]
        truth[name] = camera(position, forward)
    return FakeRoomModel(truth, points, colors, seed=seed, pose_noise=0.01, view_size=view_size)


def room_summary(room):
    """The numbers to look at after a build, in plain words."""
    low, high = np.array(room["box"]["low"]), np.array(room["box"]["high"])
    size = high - low
    lines = [
        f"{room['n_points']:,} points from {room['frames_used']} frames; colours: {'yes' if room['has_colors'] else 'NO'}",
        f"room box: {size[0]:.2f} m x {size[1]:.2f} m, {size[2]:.2f} m high"
        + ("" if room["wall_aligned"] else "  (walls not lined up with the axes, so the box is larger than the room)"),
        f"up consistency: {room['up_consistency']:.2f}  (1.00 = every frame agreed which way is up; below 0.80 is refused)",
        f"anchors kept: {len(room['anchors'])}; per-frame detail saved: {'yes' if room.get('bundle') else 'no'}",
    ]
    return "\n".join(lines)


def frames_sheet(frame_paths, out_png, n=12, title="Frames picked from the video"):
    """A grid of n frames, to check by eye that they are sharp and cover the room."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    chosen = pick_evenly(frame_paths, n)
    cols = 4
    rows = max(1, -(-len(chosen) // cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 2.4))
    for ax in np.atleast_1d(axes).ravel():
        ax.axis("off")
    for ax, path in zip(np.atleast_1d(axes).ravel(), chosen):
        with Image.open(path) as image:
            ax.imshow(image)
        ax.set_title(Path(path).name, fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=90)
    plt.close(fig)
    return Path(out_png)


def preview_png(room_dir, out_png, placements=None, label="", max_points=80_000, seed=0):
    """Top-down and side views of the room, with the camera path and any placed photos."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from roomgeom.pointsfile import read_ply, read_bin

    room_dir = Path(room_dir)
    room = load_room(room_dir)
    kind = "ply" if "ply" in room["points_files"] else "bin"
    points, colors = (read_ply if kind == "ply" else read_bin)(room_dir / room["points_files"][kind])
    if len(points) > max_points:
        pick = np.random.default_rng(seed).choice(len(points), max_points, replace=False)
        points = points[pick]
        colors = None if colors is None else colors[pick]
    shade = "0.5" if colors is None else colors / 255.0

    cameras = np.array([a["pose"] for a in room["anchors"]]) if room["anchors"] else np.zeros((0, 4, 4))
    cameras_file = room_dir / "cameras.json"
    if cameras_file.exists():
        cameras = np.array([c["pose"] for c in json.loads(cameras_file.read_text(encoding="utf-8"))["cameras"]])

    fig, (top, side) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.2, 1]})
    below_ceiling = points[:, 2] < np.percentile(points[:, 2], 97)  # hide the ceiling in the top view
    top.scatter(points[below_ceiling, 0], points[below_ceiling, 1], s=0.3,
                c=shade if colors is None else shade[below_ceiling], linewidths=0)
    side.scatter(points[:, 0], points[:, 2], s=0.3, c=shade, linewidths=0)
    if len(cameras):
        where, facing = cameras[:, :3, 3], cameras[:, :3, 2]
        top.plot(where[:, 0], where[:, 1], "-", color="black", lw=0.8, alpha=0.6)
        top.quiver(where[:, 0], where[:, 1], facing[:, 0], facing[:, 1], color="black", width=0.003,
                   scale=25, alpha=0.7)
        side.plot(where[:, 0], where[:, 2], ".", color="black", ms=3)
    for p in placements or []:
        if p.get("x") is None:
            continue
        mark = "o" if p.get("placed_by") == "ai" else "x"
        top.plot(p["x"], p["y"], mark, color="red", ms=8, mfc="none", mew=2)
        top.annotate(Path(p["photo"]).stem[:14], (p["x"], p["y"]), fontsize=7, color="red",
                     xytext=(4, 4), textcoords="offset points")
    for ax, (a, b) in ((top, ("x", "y")), (side, ("x", "z"))):
        ax.set_aspect("equal")
        ax.set_xlabel(f"{a} (m)")
        ax.set_ylabel(f"{b} (m)")
        ax.grid(alpha=0.3)
    top.set_title("From above (ceiling hidden). Line: the camera's path; arrows: where it looked")
    side.set_title("From the side. Floor at z = 0")
    if label:
        fig.suptitle(label, color="red" if label == STAND_IN_LABEL else "black", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    return Path(out_png)
