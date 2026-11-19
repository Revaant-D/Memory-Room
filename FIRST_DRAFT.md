# Memory Room: first draft (P2-A3)

Revaant Daga · INFO 490, Project 2 · 18 Nov 2026

This page is the first-draft write-up: the product scope (§1), the AI plan and the evidence so far (§2), and the progress and roadmap (§3). How to install and run the app is in [`README.md`](README.md).

**Where each first-draft requirement is met:**

| Requirement | Where |
| --- | --- |
| 1. Updated product scope | §1 below |
| 2. A Django project and at least one app | `config/` (the project); two apps, `accounts/` and `rooms/` |
| 2. At least two models, with a relationship | Five models: `User` (`accounts/models.py`); `Place`, `Scan`, `Memory`, `Pin` (`rooms/models.py`). A user has places; a place has scans and photos; a `Pin` joins a photo to a scan at x, y, z. Five migrations in `rooms/migrations/` |
| 2. Views and templates | `rooms/views.py`, `rooms/pins.py`, `accounts/views.py`; every page extends `templates/base.html` (all but the bare server-error page), and forms share one include for their fields (`templates/includes/form_fields.html`) |
| 2. Forms and user input | Sign-up (`accounts/forms.py`); a place's name, a room video, up to 50 photos at once, a caption and date (`rooms/forms.py`). Uploads are checked by their content, not only their names (`rooms/validators.py`), and each form says what is wrong |
| 2. A database-backed workflow | Add photos: the form → `memory_create` → one `Memory` row each → shown on the place's page. Place a photo: a tap in the 3D room → `pin_save` (JSON) → a `Pin` row → a dot that stays after a reload |
| 2. Logins and private data | `@login_required` on every page that holds a person's data; every lookup goes through an owner check (`rooms/access.py`), so another person's place, photo or room is "page not found" |
| 3. The AI plan and evidence | §2 below, with the first real run on a GPU (18 Nov) |
| 4. Progress and roadmap | §3 below |
| 5. GitHub and how to run it | `README.md`. 281 tests: `manage.py test`. The 3D page can be tried without a GPU: `manage.py import_room <scan> --demo` |

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
| 2 | **Memory map** | Adds photos; sees each as a dot where it was taken; places by hand the ones the AI could not | Adding many photos at once works, with captions and dates, private to their owner. The place's page is the 3D room, with placed photos as dots; tapping one flies to where it was taken and shows it. A photo with no spot yet is placed by hand: tap it, then the floor where it was taken. AI placement is coded but not yet connected to the app |
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
- **Why:** Memory Room has a larger use and a larger audience. Clearance would be used a handful of times, around a few purchases, and then lose its purpose, and it served a narrow audience that would be hard to reach. Memory Room is for anyone who wants to keep a 3D version of a place they have lived in, and it is something people come back to.
- **Wireframes:** the P2-A2 wireframes were drawn for Clearance and no longer apply. The working pages take their place; `README.md` ("Run it" and "See the 3D room without a GPU") walks through each of them.

---

## 2. AI: the plan, and the evidence so far

### The AI features

| # | AI feature | In → out | Exists today? |
| --- | --- | --- | --- |
| 1 | **Build the room** | About 60 frames from the room video → a coloured 3D point for every pixel, and where the camera was for every frame | **Works.** First run on a real video on 18 Nov (Colab T4): a recognisable room, about 10% small; a levelling bug found and fixed the same day (see Evidence) |
| 2 | **Place a photo** | A photo plus frames of the room → where the camera stood, or "can't place, ask the user" | Coded and tested with a stand-in model. Ran once on two real photos: neither placed, because the check found the run unreliable (see Evidence) |
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
- The floor is the lowest flat layer, not the fullest, and the room is levelled by the floor's own plane (added after the first run; see Evidence).
- Out of GPU memory: the build retries with fewer frames.
- Output that is not real numbers stops the run and names the fix.
- GPS and other EXIF data are stripped from the photo copies the model sees.
- `run.json` records every run, failures included: GPU, versions, seconds and peak GPU memory per step.

### Evidence

**Before the first real run:**

- 96 tests of the AI code pass (Python 3.14, 18 Nov). They use a stand-in model with known answers, so they show the steps around the model behave; they say nothing about the real model's quality.
- Full rehearsals of the notebook on the laptop with the stand-in model, the second after the fix below: every cell ran each time. A separate rehearsal with an unreadable video stopped with a plain message and still saved `run.json`.
- A review of the notebook against MapAnything's source found one real problem (bf16 chosen on a T4) and fixed it before the run.

**The first real run, 18 Nov 2026** (`room-20261118-1342`; numbers from its `run.json`, `room.json` and `placements.json`):

| | |
| --- | --- |
| GPU | Colab's free Tesla T4 (15.6 GB). fp16 was chosen by our check; PyTorch's own check had said bf16 was supported |
| Video | 88.7 s, portrait, 1080 × 1920 at 30 frames a second; the 60 sharpest frames picked in 80 s |
| Model | loaded in 124 s (5.0 GB on the GPU) |
| Building the room | all 60 frames in one try: the model pass took 36 s, the whole step 63 s, at most 10.9 GB of GPU memory |
| Result | 393,033 coloured points, from 8.9 million before the least certain fifth was dropped and the room was thinned to one point per 2 cm. The frames agreed on "up" at 0.987 (1 is perfect) |

The room is recognisable: the L-shaped floor, the walls, the bed in its alcove and the corridor, with the camera's path through them.

**What went wrong, said plainly:**

1. **The bed was taken for the floor.** The levelling step put the floor at the fullest 1 cm layer of points, and the bed top (flat, 0.7 m up) held more points than the real floor: 3,471 against 3,351. The whole room came out 0.66 m too low. Separately, "up", worked out from how the phone was held, leaned 1.9° toward the way the phone faced most, which the agreement score could not catch.
   **Fixed the same day:** the floor is now the lowest flat layer, and the room is levelled by the floor's own plane. Thirteen new tests cover the fix, including a bed top that holds more points than the floor (109 AI tests in all). The model's output was sound, so the room was corrected on the laptop (`python -m roompipe relevel`) instead of being built again: the floor was 1.92° off level and 0.656 m below the false floor. The corrected room is the one imported into the app.
2. **Size: about 10% small.** Measured against a tape, after the fix (the room turned so its walls run along the axes):

   | | Tape | Model | Difference |
   | --- | --- | --- | --- |
   | Longest straight wall | 4.75 m (187 in) | 4.22 m | −11% |
   | Longer corridor wall | 2.90 m (114 in) | 2.58 m | −11% |
   | Top of the bed above the floor | 0.76 m (30 in) | 0.69–0.70 m | −9% |
   | Ceiling height | 2.67 m (105 in) | no flat ceiling found: the phone, tilted down, saw little of it, and the points there are scattered between about 2.2 and 2.8 m | not measurable |
   | Bed length | 1.93 m (76 in) | the bed top was rebuilt only in part, and its ends cannot be told apart from the alcove's walls | not measurable |

   The tape figures are the builder's rough measurements. MapAnything's "metric" scale is about a tenth small in this room; nothing in our code corrects scale yet.
3. **Shape.** Several walls appear as two to four parallel lines, up to about 25 cm apart, so some frames do not line up exactly with the others. The corridor's long wall comes out at 13° to the room's other walls.
4. **No photo was placed.** This run had two photos, both old (August and October 2026). Neither was pinned: when the model ran again with the photos and 10 of the room's frames, those frames lined up with the first build only to within 1.16 m, against a limit of 15 cm. The check therefore answered "ask the user" for both, as designed, rather than pinning a guess. The two tries were 2.66 m and 2.25 m apart. The planned test photos taken on numbered sheets were not part of this run.

**What this changes:** a scale correction from one known length (for example the bed's height, entered by the user) is the leading candidate for the evaluation's "one improvement". Photo placement needs its own investigation before 8 Dec: why the frames line up so poorly on the second pass.

---

## 3. Progress and roadmap

| Task | Current status (18 Nov) | Responsible member | Expected completion |
| --- | --- | --- | --- |
| **Django Core Features** | Done: sign-up and login; places (create, rename, delete); room video upload; photos (many at once, captions, dates, delete); the place's page is its 3D room, with photos as dots; placing a photo by hand by tapping the floor. Each user sees only their own. 281 tests pass. Remaining: pages to switch between versions | Revaant Daga (solo) | 2 Dec |
| **Database and APIs** | Done: four models with relationships (a user's Place has Scans and Memories; a Pin joins a Memory to a Scan at x, y, z), migrations, admin; a command that imports a built room and its facts; one JSON endpoint, which saves a hand-placed photo's spot. Remaining: a fuller JSON API (a room with its pins; move or remove a pin), search and a timeline of a place's photos | Revaant Daga (solo) | 1 Dec |
| **AI Integration** | Done: the room-building and photo-placing code, in a Colab notebook, tested with a stand-in model; a command that brings a built room into the app. First real run on 18 Nov on a Colab T4; that room is in the app. Remaining: correcting the room's scale; Django starts the GPU job; the AI's placements shown in the app, with the photos it could not place highlighted for hand placement (which already works); refining a hand-placed photo; lining up two scans | Revaant Daga (solo) | 5 Dec |
| **Evaluation and Testing** | Done: 281 Django tests, 5 tests of the 3D page's geometry, and 109 AI tests; a code review of the whole first draft (18 Nov: 15 findings, 12 fixed with a test each, 3 deferred); the first real run, checked against a tape measure, is the first evaluation row (§2, Evidence). Remaining: five realistic tests in a table, two real failures, one improvement with before and after | Revaant Daga (solo) | 5 Dec |
| **Deployment** | Not started. Runs locally (SQLite, files on disk). Remaining: a live host, a GPU service, two options compared on cost, what changes at 10,000 daily users, security | Revaant Daga (solo) | 6 Dec |
| **Documentation** | Done: `README.md`, this page, a system map, the AI README, a filming guide. Remaining: `README_AI.md` and the three-minute video | Revaant Daga (solo) | 8 Dec |

**Milestones inside those rows:**

| Date | Milestone |
| --- | --- |
| 29 Nov | JSON API: a room with its pins; move a pin. Django starts the GPU job |
| 1 Dec | Search and a timeline of a place's photos (the data feature) |
| 2 Dec | Versions pages: switch between scans of a place |
| 3 Dec | Placement in the app: AI pins, and the photos it could not place highlighted for hand placement |
| 5 Dec | Refining a hand-placed photo; lining up two scans; the evaluation |
| 6 Dec | Deployment and its write-up |
| 8 Dec | `README_AI.md`, the three-minute video, final push |

**Risks, and the fallback for each:**

| Risk | Why it is a risk | Fallback |
| --- | --- | --- |
| Photo placement by the AI | It placed 0 of 2 photos in the first real run: the room's frames lined up only to within 1.16 m on the second pass (limit 15 cm) | Placing by hand already works, so every photo can still be placed. Try the alternative method (match the photo's details against the room's frames, then solve for the camera) |
| Django starting the GPU job | Not tried yet; the model needs a GPU with about 11 GB free, which the laptop does not have | Keep Colab with the `import_room` command, which already runs the same checks, and explain why in the deployment write-up |
| Versions over time | Lining up two scans of one room is untested | Show two versions side by side, each with its own photos |
| The room's scale | The first room came out about 10% small against a tape | Scale the room from one length the user enters (the leading candidate for the evaluation's "one improvement") |

**Next after this draft**, in order: Django starts the GPU job; the room page shows the AI's placements and highlights the photos it could not place; the JSON API; search and a timeline; versions; the evaluation; deployment; documentation and the video.
