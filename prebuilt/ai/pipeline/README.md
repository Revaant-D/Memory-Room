# Component: ai/pipeline (`roompipe`)

**Is:** the steps around the reconstruction model, written so that the model is one swappable function. Picking frames from a video, building a room folder, placing photos in it, and a stand-in model that lets all of that be tested with no GPU.
**Is not:** connected to Django, and not evidence about the real model.
**Needs:** `roomgeom` from `prebuilt/ai/geometry` (found automatically when both folders sit side by side), and numpy. Picking frames from a video also needs opencv. The real model needs a GPU, torch and the `mapanything` package.
**Result (16 Nov 2026):** 25 tests, all pass, with Python 3.14.3, numpy 2.5.5, opencv 5.0.0 and Pillow 13.0.0.

> **`roompipe/model.py` has never been run.** It is the only file that touches MapAnything. It was written without a GPU and without the `mapanything` package installed, following `docs/reference/stage1.py`, which has itself only run on synthetic rooms. Expect to fix it on first use. Its docstring lists what to check first. Everything else in this folder was tested with a stand-in model, which is exactly as accurate as it is told to be.

## Why it was safe to build early

There is no product decision in it. It is the T5 technical design's "build room" and "place photo" steps, written out. Whatever GPU host, points-file format and job hand-off the builder chooses, these steps are the same, and they are what the builder's first real experiment (one room video, about ten photos, in Colab) needs.

## What is in it

| File | What it does | Tested? |
| --- | --- | --- |
| `roompipe/frames.py` | `extract_frames(video, out_dir)`: cuts the video into 60 stretches and keeps the sharpest frame of each | Yes, on a 3-second video made by the test |
| `roompipe/model.py` | `run_mapanything(image_paths)`: one pass of the real model. `ModelOutput`: what any model must return. Refuses any weights but `facebook/map-anything-apache` | **Only the refusal.** The model call has never run |
| `roompipe/build.py` | `build_room(frames, run_model, out_dir)`: model → level → thin → write a room folder | Yes, with the stand-in |
| `roompipe/place.py` | `place_photos(room_dir, photos, run_model)`: two tries per batch of ten photos, then pin or ask | Yes, with the stand-in |
| `roompipe/fake.py` | `FakeRoomModel`, a made-up bedroom, and `make_demo(folder)` | Yes |
| `roompipe/__main__.py` | The command line: `demo`, `build`, `place` | `demo` yes; `build` and `place` no (they call the real model) |
| `tests/test_roompipe.py` | 25 tests | |

## The room folder

`build_room` writes one folder that holds everything later steps need:

```
my-room/
├─ room.json          n_points, box, up_consistency, wall_aligned, and each anchor's file and pose
├─ points.bin         the levelled, thinned, coloured points (T5 layout)
├─ points.ply         the same points as a standard PLY (opens in MeshLab, CloudCompare, Blender)
├─ anchors/           copies of the 20 or so frames kept as anchors
└─ placements.json    written by place_photos: one entry per photo
```

Both point files are written until the builder chooses a format. An entry in `placements.json`:

```json
{"photo": "by-the-window.jpg", "placed_by": "ai", "reason": "",
 "x": 2.11, "y": 0.6, "z": 1.49, "facing": [0.0, -1.0, 0.0],
 "gap_m": 0.01, "turn_deg": 0.3, "anchor_residual_m": 0.02}
```

`placed_by` is `"ai"` (pin it) or `null` (ask the person; `reason` says why in plain words). `x`, `y`, `z` and `placed_by` are the same things the app's `Pin` model stores.

The room folder is this component's own hand-off format. How it reaches Django is not decided: which fields land on `Scan`, where anchors are stored, and how a photo file name is matched to a `Memory`.

## Using it

**A made-up room, now, with no GPU** (this is what `prebuilt/viewer/demo/` was made with):

```powershell
cd prebuilt\ai\pipeline
& <a Python with numpy> -m roompipe demo --out $env:TEMP\demo-room --align-walls
```

**The first real run, in Colab** (never done; this is the intended shape):

1. Upload the `roomgeom` and `roompipe` folders next to the notebook. Install the model as `docs/reference/reconstruct_colab.ipynb` does.
2. `!python -m roompipe build --video room.mp4 --out my-room --align-walls`
3. Download `my-room/points.ply` and open it in MeshLab or CloudCompare. That answers "how does a real room look" before any viewer is involved.
4. `!python -m roompipe place --room my-room photo1.jpg photo2.jpg ...` prints a table: pinned or ask, position, how far apart the two tries were.
5. Download the whole `my-room` folder. `prebuilt/viewer` can show it.

`--align-walls` is off unless given, which is the technical design as written. `prebuilt/ai/geometry/README.md` explains why turning it on is recommended.

## What the tests show, and do not

They show that **if** the model's poses are good, the surrounding steps do the right thing: the floor lands at z = 0, colours stay with their points through levelling and thinning, anchors are stored in the room frame, photos are placed where they were taken (to the millimetre with exact poses, within 10 cm with 1 cm of pose noise), the two tries use different anchors, a photo whose two tries disagree is not pinned and says why, a photo taken outside the room is not pinned, 23 photos go through in three batches and come back in order, a nonsense answer becomes `null` and not `NaN` in the file, and a room filmed by walking in a straight line pins nothing and says why.

They do not show that the real model's poses are good. That is the open question the whole product rests on, and only a real run answers it.

## Things found while building it

1. **The floor finder is good to half a centimetre, not better.** It reports the middle of the fullest 1 cm slice. Fine for a room; do not expect millimetres.
2. **Nothing corrects the model's scale.** The placement fit absorbs the scale of each placement pass, but the room itself is as large as the build pass says it is. If MapAnything's "metric" output is 5% off, the room is 5% off, and so is every pin's distance. `stage1.py` dealt with this by taping one wall; this pipeline does not.
3. **Mixed photo shapes are not handled** (feasibility check, 2c). A portrait photo run with landscape anchor frames may be badly cropped by the model's image loader. `place_photos` does not detect or fix this.
4. **Anchors keep their frame's file name** (`anchors/f0003.jpg`), so each can be traced back to its moment in the video.

## What a later session still has to write

- The fixes `model.py` will need on its first real run.
- A decision, then code, for getting a room folder into Django: attaching the points file to a `Scan`, storing anchors, turning `placements.json` into `Pin` rows.
- The GPU hand-off (the design's "Django starts the build-room job on a rented GPU").
