"""Rehearse the Colab notebook on this laptop, with the stand-in model. No GPU, no real video.

    python ai/rehearse_notebook.py <empty work folder>

Run it with the AI test Python (see ai/README.md, "Running the tests"); it
needs numpy, opencv, Pillow, matplotlib and IPython. Pack the code first
(`python ai/pack_for_colab.py`), because the notebook loads the zip, not the
source folders.

It makes a 40-second test video and three photos in the work folder, then runs
every code cell of build_room_colab.ipynb in order, with STAND_IN_MODEL on.
Every cell is also compiled, so lines that only run on a GPU must at least
parse. At the end it lists the pictures the notebook showed and the files in
the room folder. Everything it makes is a MADE-UP ROOM.

What a pass proves: the cells run in order and hand each other what they
need. What it cannot prove: anything about MapAnything or a real video.
"""

import json
import shutil
import sys
from pathlib import Path

import cv2
import IPython.display
import numpy as np
from PIL import Image

AI = Path(__file__).resolve().parent
NOTEBOOK = AI / "build_room_colab.ipynb"
CODE_ZIP = AI / "dist" / "memory-room-ai.zip"


MARKER = ".memory-room-rehearsal"  # left in the work folder, so a later rehearsal may reuse it


def check_work_folder(work):
    """Stop unless `work` is new, empty, or made by an earlier rehearsal: make_inputs empties it."""
    if work.exists() and any(work.iterdir()) and not (work / MARKER).exists():
        raise SystemExit(
            f"{work} is not empty, and this script deletes what is in its work folder. "
            "Give a new or empty folder (outside the project)."
        )


def make_inputs(work):
    """A test video with moving detail (so every stretch has a sharp frame) and three photos."""
    check_work_folder(work)
    shutil.rmtree(work, ignore_errors=True)
    (work / "photos").mkdir(parents=True)
    (work / MARKER).write_text("made by ai/rehearse_notebook.py\n", encoding="utf-8")
    shutil.copyfile(CODE_ZIP, work / "memory-room-ai.zip")
    rng = np.random.default_rng(0)
    base = (rng.random((640, 720, 3)) * 255).astype(np.uint8)
    writer = cv2.VideoWriter(str(work / "room.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (360, 640))
    for i in range(1200):  # 40 s at 30 frames a second, portrait
        writer.write(np.ascontiguousarray(base[:, (i % 360):(i % 360) + 360]))
    writer.release()
    for name in ("a.jpg", "b.png", "c.jpg"):
        Image.fromarray((rng.random((800, 600, 3)) * 255).astype(np.uint8)).save(work / "photos" / name)


def main(work):
    if not CODE_ZIP.exists():
        raise SystemExit("No code zip. Run `python ai/pack_for_colab.py` first.")
    make_inputs(work)
    shown = []
    IPython.display.display = lambda picture: shown.append(picture.filename)  # record, don't draw

    space = {"__name__": "__main__"}
    for cell in json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        compile(source, cell["id"], "exec")
        print(f"--- {cell['id']}")
        exec(source, space)
        if cell["id"] == "cell-02":  # the settings cell: switch to the rehearsal
            space.update(STAND_IN_MODEL=True, LOCAL_FOLDER=str(work))

    room = space["ROOM_DIR"]
    run = json.loads((room / "run.json").read_text(encoding="utf-8"))
    print("\npictures shown:", [Path(p).name for p in shown])
    print("room folder:", sorted(p.name for p in room.iterdir()))
    print("finished:", run["finished"], "| stopped because:", run["stopped_because"])
    if not run["finished"] or len(shown) != 3:
        raise SystemExit("REHEARSAL FAILED")
    print("REHEARSAL PASSED (stand-in model: a made-up room)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]).resolve())
