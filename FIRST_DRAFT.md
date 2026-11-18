# Memory Room: first draft (P2-A3)

Revaant Daga · INFO 490, Project 2 · 18 Nov 2026

This page is the first-draft write-up: the product scope (§1), the AI plan and the evidence so far (§2), and the progress and roadmap (§3). How to install and run the app is in [`README.md`](README.md).

---

## 1. Product scope

**Memory Room.** Film a room once on your phone. It becomes a 3D room you can turn and zoom around, and the photos you took in that room show up as dots at the spots where they were taken.

**The problem.** People take hundreds of photos in the places they live, and those photos end up scattered through a camera roll that is rarely opened again. One vendor survey (Popsa, 8,000 people, reported second-hand in a trade article) found that almost three-quarters of phone photos are never looked at again. When you leave a place, you lose the place itself, and the photos taken there give you no way back into it.

**Target users.** Anyone who wants to keep the memories of a place: a first apartment, a dorm room before move-out, a family home before it is sold, a childhood bedroom.

**The value.** The room is the index: a way back into a pile of photos, organised by where you stood rather than by date.

**Three core features**

| # | Feature | What the user does | Works today (18 Nov) |
| --- | --- | --- | --- |
| 1 | **Capture** | Films the room once; gets back a 3D room to turn and zoom | Uploading the room video works in the app. The 3D room is built by an AI model in a Colab notebook, outside the app (§2), brought in with one command, and shown on a 3D page in the app |
| 2 | **Memory map** | Adds photos; sees each as a dot where it was taken; places by hand the ones the AI could not | Adding many photos at once works, with captions and dates, private to their owner. The 3D page draws placed photos as dots; tapping one shows the photo. AI placement is coded but not yet connected to the app, and hand placement is not built |
| 3 | **Versions over time** | Films the place again later; switches between versions; each photo shows in the version it belongs to | The database already allows several scans per place, and a photo's position belongs to one scan. Lining two scans up is not started |

**How it differs from what exists**

- **GausNote** (iPad) pins notes and photos in a 3D scan, but by hand, on an iPad, in a scan made by another app.
- **Scaniverse** and **Polycam** make bare 3D scans, with no photos or notes placed in them.
- **Multi Splat** and **TimeSplat 4D** step through versions of a place, but hold no photos and need finished 3D files.
- **Microsoft Photosynth** placed many photos of a place in 3D; it was retired in 2017.
- The gap Memory Room fills: **the photos you already have, placed automatically, in a browser on any phone, inside versions of the place.**

**Changes since P2-A2.** The P2-A2 idea was **Clearance**: scan a room and check whether furniture from an online store fits before you buy it ([P2-A2 submission](<docs/Clearance_Project_Idea_Description (older idea).pdf>)).

- **Kept:** the technical core. An ordinary phone video becomes a metric 3D room through MapAnything; Django; a three.js viewer.
- **Dropped:** the browser extension, the fit editor, the clearance checks, furniture detection, and ARCore camera tracking.
- **Why:** **[B4: the builder's one sentence goes here.]**

---

## 2. AI: the plan, and the evidence so far

### The AI features

| # | AI feature | In → out | Exists today? |
| --- | --- | --- | --- |
| 1 | **Build the room** | About 60 frames from the room video → a coloured 3D point for every pixel, and where the camera was for every frame | Coded and tested with a stand-in model. Not yet run on a real video; the first real run is planned for 18 Nov (see Evidence) |
| 2 | **Place a photo** | A photo plus frames of the room → where the camera stood, or "can't place, ask the user" | Coded and tested with a stand-in model. Not yet run on real photos; planned with the first real run |
| 3 | **Refine a hand-placed photo** | A photo plus the spot the user tapped → the exact spot | Planned |
| 4 | **Find a room's photos** | A large batch of photos → the ones taken in this room (date, GPS, and how much the photo looks like the room) | Planned |
| 5 | **Line up two scans** | A new scan and an older one → both in the same coordinates (needed for versions) | Planned |

### The model

**MapAnything** (Meta and Carnegie Mellon University, 2025), with the Apache-2.0 weights `facebook/map-anything-apache` pinned at revision `00f9c24`, and MapAnything's code pinned at commit `3d10cf7`. The code refuses to load any other weights, including the non-commercial set.

**Why this model:**

- It turns ordinary photos into 3D at real-world scale (metres), with no depth sensor.
- It returns a camera position for every image in the same pass. That is what places a photo: run the room's frames and an old photo together, and the photo's camera position comes out with the room's.
- One pass, with no training for each room.
- The weights' licence allows commercial use.

**Alternatives considered:**

| Alternative | Why not now |
| --- | --- |
| Classic photogrammetry (for example COLMAP) | Slow, and fails on blank walls, which rooms are full of |
| Gaussian splats | The most photo-like, but each room needs GPU training. A later upgrade: MapAnything documents an export for it |
| A depth sensor (LiDAR, ARCore depth) | Needs a native app and a LiDAR phone; the builder's phone has none |
| VGGT (Meta, 2025) | Similar abilities, but its commercial-use weights are released only on request |
| Depth Anything 3 | Its smaller models are Apache-licensed. Kept as the backup if MapAnything's room disappoints; not tried yet |

**Feasibility, checked against MapAnything's source code before the first run:**

- **GPU memory.** The weights are 4.9 GB and a free Colab T4 has 16 GB. MapAnything gives no guidance for 60 images on 16 GB, so the notebook tries 60 frames, then 40, then 30 if the GPU runs out of memory.
- **Number format.** A T4 has no real support for bf16, and MapAnything's own check can still choose it there. Our code picks fp16 on older GPUs, and stops with a plain message naming the fix (fp32) if the output is not real numbers.
- **Why the room is filmed in portrait.** MapAnything forces every image in one pass to a single shape, chosen from their average proportions. Phone photos are mostly portrait, so landscape room frames would crop them.
- **Detail.** The model works at 518 pixels on the long side, and the room is thinned to one point per 2 cm. The result is a dotted room, not a photo-like one.
- **Weights quality.** Meta says the non-commercial weights perform best and gives no numbers for the gap. We use the weaker, Apache set on purpose.

### Input and output

**Building the room:**

```
room video ─► the 60 sharpest frames ─► MapAnything ─► a 3D point for each pixel + a camera for each frame
          ─► levelled (floor at height 0) and thinned ─► points.ply, the cameras, 20 anchor frames, room.json, run.json
```

**Placing photos:**

```
up to 10 photos + 10 of the 20 anchor frames ─► MapAnything ─► a position for each photo   (try 1: even-numbered anchors)
up to 10 photos + the other 10 anchors       ─► MapAnything ─► a second position         (try 2: odd-numbered anchors)
both tries agree (within 0.7 m and 30°, anchors fit within 15 cm, inside the room) ─► pin the photo
otherwise                                                                          ─► "ask the user"
```

The four limits are starting guesses, to be tuned on real photos.

### How it works with Django

**For the first draft (by hand):**

1. The phone uploads the room video to a place in the app. It is stored as a `Scan`.
2. The same video goes through the Colab notebook (`ai/build_room_colab.ipynb`), which writes a room folder and a zip to Google Drive.
3. A management command, `import_room`, reads the downloaded room folder, stores `points.ply` in `Scan.points_file`, and marks the scan "ready".
4. The place's page links to a 3D viewer page (three.js), which loads the points through an owner-checked address.

**By 8 Dec (inside the app):**

- A Django view starts the GPU job itself. The proposal is Modal: Django starts the job and checks back for the result, so the GPU service never has to call Django.
- The result goes through the same import code.
- Each placed photo becomes a `Pin` row (photo, scan, x, y, z) with `placed_by = "ai"`. Photos the AI could not place are highlighted for the user to place by hand.

### Reliability already built

- Only the Apache weights load.
- Unreadable images are counted and reported, not silently skipped.
- A tilted video, or no floor in view, stops the run with "film again" and the reason.
- Out of GPU memory: the build retries with fewer frames.
- Output that is not real numbers stops the run and names the fix.
- GPS and other EXIF data are stripped from the photo copies the model sees.
- `run.json` records every run, failures included: GPU, versions, seconds and peak GPU memory per step.

### Evidence

**Before the first real run:**

- 96 tests of the AI code pass (Python 3.14, 18 Nov). They use a stand-in model with known answers, so they show the steps around the model behave; they say nothing about the real model's quality.
- Full rehearsals of the notebook on the laptop with the stand-in model, the second after the fix below: every cell ran each time. A separate rehearsal with an unreadable video stopped with a plain message and still saved `run.json`.
- A review of the notebook against MapAnything's source found one real problem (bf16 chosen on a T4) and fixed it before the run.

**The first real run (planned for 18 Nov): not done yet.** _To be filled in from the run's `run.json`, `room.json` and `placements.json`, and the room measured with a tape (step C8). If the run fails, its failure and error are reported here instead._

---

## 3. Progress and roadmap

<!-- B7: the builder confirms these dates. -->

| Task | Current status (18 Nov) | Responsible member | Expected completion |
| --- | --- | --- | --- |
| **Django Core Features** | Done: sign-up and login; places (create, rename, delete); room video upload; photos (many at once, captions, dates, delete); a 3D room page for each built scan, with photos as dots. Each user sees only their own. 240 tests pass. Remaining: placing a photo by hand on the 3D page, pages to switch between versions | Revaant Daga (solo) | 2 Dec |
| **Database and APIs** | Done: four models with relationships (a user's Place has Scans and Memories; a Pin joins a Memory to a Scan at x, y, z), migrations, admin; a command that imports a built room and its facts. Remaining: a JSON API (a room with its pins; move a pin), search and a timeline of a place's photos | Revaant Daga (solo) | 1 Dec |
| **AI Integration** | Done: the room-building and photo-placing code, in a Colab notebook, tested with a stand-in model; a command that brings a built room into the app. Not yet run on a GPU (the first real run is planned for 18 Nov). Remaining: Django starts the GPU job; placement with highlighted photos and hand placement; refining a hand-placed photo; lining up two scans | Revaant Daga (solo) | 5 Dec |
| **Evaluation and Testing** | Done: 240 Django tests and 96 AI tests; a code review of the whole first draft (18 Nov: 15 findings, 12 fixed with a test each, 3 deferred); the first real run will be the first evaluation row. Remaining: five realistic tests in a table, two real failures, one improvement with before and after | Revaant Daga (solo) | 5 Dec |
| **Deployment** | Not started. Runs locally (SQLite, files on disk). Remaining: a live host, a GPU service, two options compared on cost, what changes at 10,000 daily users, security | Revaant Daga (solo) | 6 Dec |
| **Documentation** | Done: `README.md`, this page, a system map, the AI README, a filming guide. Remaining: `README_AI.md` and the three-minute video | Revaant Daga (solo) | 8 Dec |

**Milestones inside those rows:**

| Date | Milestone |
| --- | --- |
| 29 Nov | JSON API: a room with its pins; move a pin. Django starts the GPU job |
| 1 Dec | Search and a timeline of a place's photos (the data feature) |
| 2 Dec | Versions pages: switch between scans of a place |
| 3 Dec | Placement in the app: AI pins, highlighted photos, hand placement |
| 5 Dec | Refining a hand-placed photo; lining up two scans; the evaluation |
| 6 Dec | Deployment and its write-up |
| 8 Dec | `README_AI.md`, the three-minute video, final push |

**Next after this draft**, in order: Django starts the GPU job; the viewer shows AI-placed photos and lets the user place the rest; the JSON API; search and a timeline; versions; the evaluation; deployment; documentation and the video.
