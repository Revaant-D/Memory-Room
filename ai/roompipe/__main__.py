"""Command line for roompipe. Run from ai/ (the folder holding roompipe and roomgeom):

    python -m roompipe demo  --out demo-room
    python -m roompipe build --video room.mp4 --out my-room
    python -m roompipe place --room my-room photo1.jpg photo2.jpg ...
    python -m roompipe relevel --room old-room.zip --out new-room

`demo` needs only numpy and uses the stand-in model: it makes a made-up room.
`relevel` needs numpy (and matplotlib for the new preview pictures): it
corrects a room built before the floor fix of 18 Nov 2026, without the GPU.
`build` and `place` call the real model and need a GPU, torch, the
mapanything package and opencv. They have never been run. The Colab notebook
(ai/build_room_colab.ipynb) is the intended way to run them.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from roompipe.build import build_room
from roompipe.place import place_photos, summary_lines


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m roompipe", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("demo", help="write a made-up room folder with the stand-in model")
    p.add_argument("--out", required=True)
    p.add_argument("--align-walls", action="store_true")
    p.add_argument("--spacing", type=float, default=0.02, help="metres between demo points")

    p = sub.add_parser("build", help="room video or frames -> room folder (real model)")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--video")
    source.add_argument("--frames-dir", help="a folder of frames already picked, in name order")
    p.add_argument("--out", required=True)
    p.add_argument("--n-frames", type=int, default=60)
    p.add_argument("--align-walls", action="store_true")
    p.add_argument("--format", choices=["bin", "ply", "both"], default="both")

    p = sub.add_parser("place", help="place photos in a built room (real model)")
    p.add_argument("--room", required=True)
    p.add_argument("photos", nargs="+")

    p = sub.add_parser("relevel", help="correct the levelling of a room folder or zip (no GPU)")
    p.add_argument("--room", required=True, help="the room folder or its zip; it is not changed")
    p.add_argument("--out", required=True, help="a new or empty folder for the corrected room")

    args = parser.parse_args(argv)

    if args.command == "relevel":
        return _relevel(args.room, args.out)

    if args.command == "demo":
        from roompipe.fake import make_demo

        room, results = make_demo(args.out, spacing=args.spacing, align_walls=args.align_walls)
        print(f"MADE-UP ROOM (stand-in model, not a reconstruction): {args.out}")
        print(f"{room['n_points']} points, {len(room['anchors'])} anchors")
        print("\n".join(summary_lines(results)))
        return 0

    from functools import partial

    from roompipe.model import run_mapanything

    if args.command == "build":
        build_model = partial(run_mapanything, keep_views=True)  # also save frames, cameras, per-pixel points
        formats = ("bin", "ply") if args.format == "both" else (args.format,)
        with tempfile.TemporaryDirectory() as scratch:
            if args.video:
                from roompipe.frames import extract_frames

                frames = extract_frames(args.video, Path(scratch) / "frames", args.n_frames)
                if len(frames) < 30:
                    print(f"only {len(frames)} frames could be read; film a longer video", file=sys.stderr)
                    return 1
            else:
                frames = sorted(
                    p for p in Path(args.frames_dir).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")
                )
            room = build_room(frames, build_model, args.out, align_walls=args.align_walls, formats=formats)
        print(f"room written to {args.out}: {room['n_points']} points, {len(room['anchors'])} anchors,")
        print(f"up consistency {room['up_consistency']}, colours: {room['has_colors']}")
        return 0

    results = place_photos(args.room, args.photos, run_mapanything)
    print("\n".join(summary_lines(results)))
    return 0


def _relevel(source, out):
    from roompipe.relevel import relevel_room_folder

    try:
        room = relevel_room_folder(source, out)
    except ValueError as problem:
        print(problem, file=sys.stderr)
        return 1
    record = room["relevelled"]
    tilt = record["floor_tilt_deg"]
    print(f"re-levelled room written to {out}")
    print(f"up from: {record['up_from']}; the floor was {tilt} degrees off level"
          if tilt is not None else "no floor plane found; only the height was corrected")
    print(f"the floor was at z = {record['floor_was_at_m']} m in the old frame; it is now at z = 0")
    low, high = room["box"]["low"], room["box"]["high"]
    print("box (m): " + ", ".join(f"{a} {lo:.2f} to {hi:.2f}" for a, lo, hi in zip("xyz", low, high)))
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("matplotlib is not installed, so the preview pictures were not redrawn", file=sys.stderr)
        return 0
    from roompipe.session import preview_png

    out = Path(out)
    run = json.loads((out / "run.json").read_text(encoding="utf-8")) if (out / "run.json").is_file() else {}
    label = f"{run.get('run_name', out.name)}: re-levelled on {record['at']}"
    preview_png(out, out / "preview.png", label=label)
    placements_file = out / "placements.json"
    if placements_file.is_file():
        placements = json.loads(placements_file.read_text(encoding="utf-8"))
        preview_png(out, out / "preview-photos.png", placements, label=label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
