# Component: ai/geometry (`roomgeom`)

**Is:** the arithmetic of the AI part with the AI taken out. Three small numpy modules that turn the reconstruction model's output into the room frame, place a photo from model poses, and decide whether to trust the placement.
**Is not:** anything that calls the model, reads a video, or talks to Django. It is not a kit and `kit.py` does not know about it. The steps that use it (frames, the model call, the room folder) are next door in `prebuilt/ai/pipeline`.
**Result (16 Nov 2026):** 37 tests, all pass, with Python 3.14.3 and numpy 2.5.5, on made-up data only.

> **Never run on real model output.** Every test builds a fake room whose true shape is known and checks the maths recovers it. That proves the arithmetic. It says nothing about whether MapAnything's poses are good enough for the method to work on a real room. `docs/reference/06-I-M2-technical-feasibility-check.md` lists the reasons it might not.

## Why it was safe to build early

There is no product decision in it. It implements the method already written in the T5 technical design (`docs/reference/T5-I-M2-memory-room-technical.pdf`, "Level, thin, keep anchors" and "Placing a photo, and knowing when not to"), and whatever model, GPU host or points-file format the builder later chooses, this arithmetic is the same. If the builder drops the anchor-fit method for another (the feasibility check suggests giving the model the anchors' known poses instead), `fit.py` and `place_from_poses` go unused; `level.py` and `check_two_tries` still apply.

## What is in it

| File | What it does |
| --- | --- |
| `roomgeom/fit.py` | `umeyama(src, dst)`: the scale, rotation and shift that carry one set of points onto another. `apply_fit`, `fit_residuals`. `spread` and `on_a_line`: is a set of anchors spread out enough to fit from? |
| `roomgeom/level.py` | `level_room(points, poses)`: find up, find the floor, turn everything so the floor is z = 0 and z is up, thin the points, pick about 20 anchor frames, measure the room's box. Raises `Refilm` when the phone was tilted too much or the floor was not filmed |
| `roomgeom/place.py` | `place_from_poses(run_poses, anchor_room_poses)`: one model pass's poses → where each photo was taken, in the room. `check_two_tries(...)`: compare two passes and say, per photo, pin it (`placed_by="ai"`) or ask the person (`None`, with a plain reason). `Thresholds` holds the four numbers |
| `roomgeom/pointsfile.py` | Writes and reads the room's points file in **both** candidate formats, `bin` (the T5 layout) and `ply` (standard PLY). The format is the builder's open decision; this makes either one ready and lets the two be compared on a real room first |
| `tests/test_roomgeom.py`, `tests/test_pointsfile.py` | 29 and 8 tests |
| `requirements.txt` | numpy, and nothing else |

`estimate_up`, `floor_height` and `voxel_downsample` are copied from `docs/reference/stage1.py` so the folder runs on its own. The one change: `voxel_downsample` returns its indices sorted.

## How it fits the rest

```
room video ─► pick frames ─► MapAnything ─► points, poses        (stage1.py / Colab; never run on a real room)
                                               │
                                level_room() ◄─┘                 roomgeom.level
                                     │
              room points, anchors, box, all in the room frame   ─► points file (format undecided) ─► viewer
                                     │
photos + half the anchors ─► MapAnything ─► poses                (not written yet)
                                               │
                          place_from_poses() ◄─┘   (twice, with the two halves)      roomgeom.place
                                     │
                           check_two_tries()
                                     │
                 placed_by "ai"  ─► Pin(memory, scan, x, y, z, placed_by="ai")       rooms/models.py (chunk 2)
                 placed_by None  ─► ask the person; they tap the spot ─► Pin(..., placed_by="user")
```

The result of `check_two_tries` lines up with the `Pin` model on purpose: `pos` is x, y, z in metres in the scan's own frame with the floor at z = 0, and `placed_by` is the same word the model stores. A `Pin` refuses "not a number"; `check_two_tries` never proposes one.

## Running the tests

numpy is **not** in the project's `.venv` (the Django app does not need it). Use any Python that has it. The tests were run from a throwaway environment:

```powershell
py -3.14 -m venv $env:TEMP\roomgeom-venv
& $env:TEMP\roomgeom-venv\Scripts\python.exe -m pip install numpy
cd prebuilt\ai\geometry
& $env:TEMP\roomgeom-venv\Scripts\python.exe -m unittest discover -s tests
```

In Colab, numpy is already there: upload the `roomgeom` folder next to the notebook and `import roomgeom`.

## Things found while building it that the builder should hear

1. **The "inside the room" check in the design is looser than it looks.** The design turns the room so the floor is flat but leaves the walls at whatever angle they came out. A box drawn around a 4 m × 3 m room sitting at 45° is 4.9 m × 4.9 m, so a photo placed well outside the walls still counts as "inside". A test records this. `level_room(..., align_walls=True)` adds a turn that lines the walls up with the axes, after which the box fits the room (tested: within 12 cm on a made-up rectangular room). It also makes one floor corner the origin, so a pin at (2.1, 0.6, 1.5) reads as "2.1 m along the long wall, 0.6 m along the short one, 1.5 m up"; without it x and y are measured from wherever the model's own origin happened to fall. It is **off by default**, so the default behaviour is the design as written. Recommendation: turn it on. It also makes the viewer open square-on to a wall. For an L-shaped room the box still overstates the room; a proper fix would test against the walls, not a box.
2. **Anchors standing nearly in a line make the fit meaningless**, and the design's sketch would not notice. `place_from_poses` now refuses them (`on_a_line`, with a 5 cm starting guess). A person who films by walking straight across a room, not around it, would hit this.
3. **A mirror-image fit is possible when all anchors are at one height**, which is the normal case (a phone held at chest height all the way round). The sketch's guard against it is kept and a test proves a photo taken above or below that height lands on the correct side.
4. **The feasibility check's criticism of the two-try check stands.** Both tries use the same model and the same photo, so a confidently wrong answer can repeat in both. Nothing here fixes that.

## The two points-file formats, side by side

Both hold the same thing: per point, a position (three 32-bit floats, metres) and a colour (three bytes). 15 bytes a point; a 100,000-point room is 1.5 MB either way.

| | `bin` | `ply` |
| --- | --- | --- |
| What it is | The layout in the T5 sketch: all positions, then all colours, no header | The standard PLY format, binary, with a short text header |
| Size | 15 bytes a point | 15 bytes a point plus about 230 bytes |
| Reading it in the browser | Two lines, no copying | A loop over the points (about 25 lines in `prebuilt/viewer/loaders.js`) |
| Opening it without the app | Nothing can | MeshLab, CloudCompare, Blender |
| Says what it is | No. A damaged or wrong file is only caught if its size is not a multiple of 15 | Yes. The header names the fields and the count, and a short file is caught |
| In this repository | `.gitignore` already excludes `*.bin` | Not excluded |

Not a recommendation the builder has to take, but for the record: being able to open the first real room in MeshLab before any viewer exists is worth more than the two lines saved.

## The numbers, all starting guesses

| Number | Value | Where |
| --- | --- | --- |
| Anchors must line up within | 0.15 m | `Thresholds.anchor_residual_m` |
| Two tries must agree on position within | 0.7 m | `Thresholds.gap_m` |
| ... and on direction within | 30° | `Thresholds.turn_deg` |
| A spot may be this far outside the box | 0.3 m | `Thresholds.box_margin_m` |
| Up is trusted when frames agree at least | 0.8 | `level_room(least_consistency=...)` |
| One point kept per cube of side | 2 cm | `level_room(voxel=...)` |
| Anchors kept | about 20 | `pick_anchors(about=...)` |
| Anchors count as "on a line" below a second spread of | 5 cm | `on_a_line(least_second_spread=...)` |

The first seven are the design's. The last is new. The design says the thresholds are to be set by the ten-photo test.

## What a later session still has to write

- The model call for placement is drafted in `prebuilt/ai/pipeline/roompipe/model.py` but has never been run. The feasibility check, section 2c, warns that the image loader forces every image to one shape, so portrait photos mixed with landscape frames need handling.
- Choosing the points-file format (both are written and read here; the browser side is in `prebuilt/viewer/loaders.js`).
- Storing anchors (the design defers an Anchor model to "with the GPU job").
- The hand-off between Django and the GPU.
