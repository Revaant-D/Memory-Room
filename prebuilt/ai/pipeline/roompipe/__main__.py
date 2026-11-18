"""Command line for roompipe. Run from prebuilt/ai/pipeline (or with both folders on the path):

    python -m roompipe demo  --out demo-room
    python -m roompipe build --video room.mp4 --out my-room
    python -m roompipe place --room my-room photo1.jpg photo2.jpg ...

`demo` needs only numpy and uses the stand-in model: it makes a made-up room.
`build` and `place` call the real model and need a GPU, torch, the
mapanything package and opencv. They have never been run.
"""

import argparse
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

    args = parser.parse_args(argv)

    if args.command == "demo":
        from roompipe.fake import make_demo

        room, results = make_demo(args.out, spacing=args.spacing, align_walls=args.align_walls)
        print(f"MADE-UP ROOM (stand-in model, not a reconstruction): {args.out}")
        print(f"{room['n_points']} points, {len(room['anchors'])} anchors")
        print("\n".join(summary_lines(results)))
        return 0

    from roompipe.model import run_mapanything

    if args.command == "build":
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
            room = build_room(frames, run_mapanything, args.out, align_walls=args.align_walls, formats=formats)
        print(f"room written to {args.out}: {room['n_points']} points, {len(room['anchors'])} anchors,")
        print(f"up consistency {room['up_consistency']}, colours: {room['has_colors']}")
        return 0

    results = place_photos(args.room, args.photos, run_mapanything)
    print("\n".join(summary_lines(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
