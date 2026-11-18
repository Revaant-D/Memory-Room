# ai/: building the 3D room

The AI part of Memory Room, kept apart from the Django app. Django does not import anything here yet; for the first draft the room is built in Google Colab and its result is brought into the app afterwards.

**Status, 18 Nov 2026:** written and rehearsed; **first real run on 18 Nov at 13:42 UTC** on a Colab T4 (`room-20261118-1342`). The model ran cleanly, but the levelling step took the bed top for the floor. That was fixed the same day, and the room was corrected on the laptop with `python -m roompipe relevel` (see "Changes after the first real run").

## What is here

```
ai/
├─ build_room_colab.ipynb   the notebook: room video in Drive -> 3D room folder back in Drive
├─ pack_for_colab.py        makes dist/memory-room-ai.zip, the code the notebook loads
├─ rehearse_notebook.py     runs every notebook cell on a laptop with the stand-in model
├─ roompipe/                the steps around the model
│  ├─ frames.py             the sharpest frame from each of 60 stretches of the video
│  ├─ model.py              the one call to MapAnything (Apache weights only, pinned revision)
│  ├─ build.py              frames -> model -> levelled room folder
│  ├─ place.py              photos -> model twice -> pin or ask (the plan's method)
│  ├─ session.py            the notebook's helpers: run record, retries, photo copies, pictures
│  ├─ relevel.py            corrects the levelling of a room already built (no GPU)
│  └─ fake.py               a stand-in model and a made-up room, for tests and rehearsals
├─ roomgeom/                the geometry, numpy only: level the room, fit, the pin-or-ask check, point files
├─ tests/                   109 tests, all with the stand-in model
└─ requirements.txt         what the tests need on a laptop
```

`roompipe` and `roomgeom` were built ahead of time in `prebuilt/ai/` on 16 Nov and copied here on 17 Nov, when the notebook needed them. What changed on the way is listed under "Changes since prebuilt/" below.

## Running the notebook

1. On the laptop: `python ai/pack_for_colab.py` (any Python). It writes `ai/dist/memory-room-ai.zip`.
2. In Google Drive, make a folder `MemoryRoom` in My Drive. Put in it the room video, the zip, and optionally a folder `photos`.
3. Open `ai/build_room_colab.ipynb` in Colab (colab.research.google.com → File → Upload notebook). It asks for a GPU runtime by itself; check it says T4 under Runtime → Change runtime type.
4. Runtime → Run all. Allow access to Drive when asked.
5. The result lands in `MyDrive/MemoryRoom/rooms/<run name>/`, with a zip beside it.

## What one run produces

| File | What it is |
| --- | --- |
| `room.json` | Point count, the room's box in metres, how well the frames agreed on "up", the anchors and their poses, the move from the model's frame to the room frame, and the model's facts (weights revision, confidence cut-off) |
| `points.ply`, `points.bin` | The coloured points, levelled (floor at z = 0, z up) and thinned to one per 2 cm, in the two candidate formats. PLY opens in MeshLab and CloudCompare |
| `anchors/` | About 20 of the frames, at full size, for placing photos |
| `frames/`, `cameras.json`, `dense.npz` | Every frame as the model saw it, its camera (pose and intrinsics), and the 3D point behind every pixel. Kept so another way of placing photos can be tried later without running the model again |
| `placements.json` | One entry per photo: pinned or ask, where, and how far apart the two tries were |
| `preview.png`, `preview-photos.png`, `frames-sheet.png` | Pictures to check by eye |
| `run.json` | What ran: GPU, weights revision, MapAnything commit, the code zip's fingerprint, seconds and peak GPU memory per step and per model call, frames tried, and anything that failed |

Everything in a room folder shows the inside of someone's room. It is not put in git.

## Running the tests

```powershell
py -3.14 -m venv $env:TEMP\ai-venv
& $env:TEMP\ai-venv\Scripts\python.exe -m pip install -r ai\requirements.txt
cd ai
& $env:TEMP\ai-venv\Scripts\python.exe -m unittest discover -s tests
```

To rehearse the whole notebook with the stand-in model (every cell, a made-up room), from the project folder after packing the zip:

```powershell
& $env:TEMP\ai-venv\Scripts\python.exe ai\rehearse_notebook.py <an empty folder outside the project>
```

It ends with `REHEARSAL PASSED` or `REHEARSAL FAILED`. It needs IPython, which is in `requirements.txt` for this reason.

109 tests passed on 18 Nov 2026, after the floor fix (Python 3.14.3 and the versions in `requirements.txt`). They prove the steps around the model behave given model output of known accuracy. They prove nothing about the real model.

## How it was checked on 17 Nov

- **Against MapAnything's source** at commit `3d10cf7`: the call to `infer()` and its arguments, the output names (`pts3d`, `conf`, `mask`, `camera_poses`, `intrinsics`, `img_no_norm`), and how `load_images` reads a list of files (in the order given; it silently skips unreadable ones, so the count is now checked).
- **The whole notebook, rehearsed** on this laptop with the stand-in model: a 20-second test video, three photos (one rotated with GPS data, one PNG, one broken). Every cell ran; the rotated photo came out upright with no EXIF; the broken one was reported, not dropped. A second rehearsal with an unreadable video stopped with a plain message and still saved `run.json`.
- **Re-checked against MapAnything's source at `3d10cf7`, the evening of 17 Nov,** before the first real run:
  - `load_images` keeps the list order, skips unreadable files without a word, and crops every image to one shape chosen from their average proportions.
  - The `infer()` arguments and the shapes of its outputs match what `model.py` reads.
  - The pinned weights revision exists and is public: no login or token is needed.
  - The dependencies do not pin PyTorch, so Colab's own copy stays. They do pin `opencv-python-headless==4.10.0.84` over Colab's OpenCV.
  - **One problem found and fixed:** MapAnything picks bf16 or fp16 with `torch.cuda.is_bf16_supported()`, which can answer yes on a T4, where bf16 is only emulated. `model.py` now chooses from the GPU generation (`amp_dtype_for`: fp16 below compute capability 8, the rule Meta's VGGT uses).
- **Rehearsed again after those changes,** with the stand-in model, a 40-second test video and three photos: every cell ran, all three check pictures were made, and every room file was written.
- **Not checked:** anything on a GPU; the install of MapAnything in Colab; whether fp16 gives clean numbers on a T4 (the run stops with a plain message if it does not); whether 60 frames fit in a T4's 16 GB; how long a real run takes; whether the real room looks right.

## Changes since prebuilt/

- `model.py`: the images go to `load_images` as a list instead of being copied to a temporary folder; the number read is checked; the weights revision is pinned (`00f9c24`, latest on 17 Nov 2026) and the MapAnything commit recorded (`3d10cf7`); `keep_views=True` also returns each frame's picture, per-pixel points, confidence, valid pixels and intrinsics; non-image files are refused before anything loads.
- `build.py`: `room.json` records the move from the model's frame to the room frame and the model's facts; with `keep_views`, it also writes `frames/`, `cameras.json` and `dense.npz`.
- `fake.py`: the stand-in can return per-frame detail too.
- `session.py`: new; the notebook's helpers.
- `model.py`, evening of 17 Nov: the number format is chosen from the GPU generation (`precision`, default `"auto"`) and recorded in the output; a pass whose camera positions, or more than 1% of whose points, are not real numbers stops with a sentence saying how to switch to fp32; the few invalid points of an otherwise good pass are dropped and counted.
- The notebook, evening of 17 Nov: a `PRECISION` setting; a check right after the install that OpenCV still loads; the GPU's compute capability and the precision used go into `run.json`; the frames sheet now says to stop if the frames are sideways; the first cell points to `docs/filming-guide.md`.
- `__init__.py`, `__main__.py`: paths and help text for this folder; the command line's `build` keeps the per-frame detail.

## Changes after the code review of 18 Nov

- `roompipe/place.py`: a model pass that fails is no longer recorded as "ask the person" for every photo in the batch. It stops placement, and the notebook writes the failure into `run.json`.
- `roomgeom/place.py`: the "inside the room" check looks at the spot that is pinned (the middle of the two tries), not at the first try.
- The notebook: a run starts with an empty room folder, and the save never merges into, or writes over, an earlier Drive folder of the same name (a new name gets the time added).
- `rehearse_notebook.py`: refuses a work folder that holds anything except an earlier rehearsal, because it empties that folder.
- The code zip was re-packed after these changes and the notebook rehearsed again (passed).

## Changes after the first real run (18 Nov)

**What the run showed.** `room-20261118-1342`: Colab T4, fp16, 60 frames in one try, 393,033 points, peak 10.9 GB. The model's output was sound, but the room came out 0.66 m too low. `floor_height` kept the fullest 1 cm slice below the cameras, and the builder's bed top (flat, 0.71 m up) beat the real floor by 3,471 points to 3,351. The floor had lost because "up", averaged from how the phone was held, leaned 1.9° toward the way the phone faced most, which spread the floor over several slices. The phone's agreement score (0.987) could not catch that.

**The fix (the builder's choice, 18 Nov).**
- `roomgeom/level.py`: `floor_layer` takes the **lowest** run of slices that stand out from the walls, not the fullest slice. `floor_plane` fits the floor's own plane by RANSAC, among planes within 15° of the phone's up, then refines it on every point near it. `level_room` levels by that plane. `room.json` gains `up_from` and `floor_tilt_deg`. Tests: a bed top fuller than the floor, a phone that leans 9°, a 30° ramp (never taken for the floor).
- `roompipe/relevel.py` and `python -m roompipe relevel --room <room folder or zip> --out <new folder>`: corrects a room built before the fix, with no GPU. It moves every room-frame number (points, anchors, cameras, per-pixel points, placements, the move from the model's frame), recomputes the box, records what it did under `relevelled` in `room.json`, and redraws the preview pictures. The source is never changed. Tests: a correct room, broken by a known tip and drop in every file, comes back right.

**The first room, re-levelled** (`room-20261118-1342-relevelled`, kept beside the zip in the builder's Downloads, not in git): the floor was 1.92° off level and 0.656 m below the false floor; it is now at z = 0. The camera path is at 1.15 to 1.4 m, the bed top at about 0.7 m, the top of the room at 2.77 m (the box's top, ignoring the highest 1% of points). The app's import check accepts it. The code zip was re-packed with the fix and the notebook rehearsed again (passed).

## Decisions still open that touch this folder

- The points-file format (PLY or the T5 `bin` layout). Both are written until it is decided.
- Turning the room so its walls line up with the axes (`ALIGN_WALLS` in the notebook). Off, as the design is written.
- How a room folder reaches Django: which fields land on `Scan`, and how a photo's file is matched to a `Memory`.
- The placement method for the test. The notebook runs the plan's (two tries, pin if they agree).
