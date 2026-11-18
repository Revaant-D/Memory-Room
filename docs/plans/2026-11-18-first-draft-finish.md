# Finishing the first draft: the run sheet for Wednesday 18 Nov 2026

**Written:** the evening of Tue 17 Nov 2026, at the end of a session, so that a fresh session can carry on with no other context.
**Deadline:** the first draft pushed to GitHub and the URL submitted on Canvas by **Wed 18 Nov 2026, 11:59 PM** (the builder's own target; the class date was 9 Nov).

This is the single ordered list of everything left before the first draft: who does each step, what it needs, and how to tell it is done.

## How to use this file

- **A fresh Claude session:** read `CLAUDE.md` first (the rules), then this file from top to bottom. Then start at the first unticked **C** step in the Status table whose "Needs" are met. Do not reopen anything under "Already decided".
- **Steps are marked B or C.** **B** steps are done by the builder, **C** steps by Claude. The two tracks run at the same time. A **Sync** row is where one track waits for the other.
- **Keep this file current; it is the handoff.** When a step is done, tick it in the Status table with the date and a one-line result: test counts, file names, what failed.
- **The four-step rule in `CLAUDE.md` still holds** (decide, build, walk through, record). Claude makes small calls itself and lists them at the end of the session so the builder can overrule any. Anything that changes how the product behaves goes to the builder first.
- **Commit and push only when the builder says so** (step B7).

## Status

| Step | Who | What | Needs | Status |
| --- | --- | --- | --- | --- |
| B0 | B | Confirm where the model runs: Colab (recommended) or the laptop GPU | — | ☑ 18 Nov, ~00:30. **Colab** (builder) |
| B1 | B | Film the room, take the placement photos, measure the room | — | ◐ 18 Nov: filmed. The room is tight (a bed in a corner, a corridor of about 5 ft), so no loop: corridor passes both ways, an arm's-length swing at the far end, a pass from the bed, three paper sheets instead of five. Photos and tape measurements still to come |
| B2 | B | Put the video, photos and code zip in Drive; run the Colab notebook | B1 | ☑ 18 Nov, 13:42 UTC (7:42 AM Chicago), `room-20261118-1342`. T4, fp16, 60 frames in one try, 393,033 points, no problems; build 63 s, peak 10.9 GB. Video 88.7 s. Only 2 photos in `photos/`, both old and landscape; both "ask" (anchors re-matched only to 1.16 m) |
| B3 | B | Download the room zip to Downloads; tell Claude its path; copy the room video to the laptop | B2 | ◐ Zip `room-20261118-1342.zip` in the builder's Downloads (unpacked for reading in Claude's scratchpad, not in the project). Video not yet uploaded to the app as a scan |
| B4 | B | Say in one sentence why Memory Room replaced Clearance | — | ☐ |
| B5 | B | Decide how the instructor reaches the private repository | — | ☐ |
| C1 | C | Apply chunk 5 (photos) from the `D2a-D3a` kit | — | ☑ 18 Nov, ~00:05. Verify all `ok`; applied `chunk5-parts` + `chunk5-D2a-D3a`; no migration; **195 tests pass**; real server 14/14 + `/media/` path 404. Recorded: system map piece 7, plan "As built (chunk 5)", features.md |
| C2 | C | `FIRST_DRAFT.md`, section 1: product scope (requirement 1) | B4 for one sentence | ◐ 18 Nov, by ~00:10. Written; the "Why" line holds a marked placeholder until B4 |
| C3 | C | `FIRST_DRAFT.md`, section 3: progress and roadmap (requirement 4) | — | ☑ 18 Nov, by ~00:10. The brief's six rows plus a milestones table; dates are the proposal, for B7 to confirm. Update the status cells after C6/C7 |
| C4 | C | `FIRST_DRAFT.md`, section 2: AI plan, written before the run (requirement 3) | — | ☑ 18 Nov, by ~00:10. "The first real run" line is a placeholder for C8. AI tests re-run: 91 pass |
| C5 | C | `README.md` (plan chunk 6, Task 13) | C1 | ☑ 18 Nov, by ~00:10. Written from what has run; add `import_room` and the viewer page once C6/C7 are built. Clean-copy check is in C10 |
| Push 1 | C | Early push, at the builder's word (18 Nov, commits at 00:44) | — | ☑ Branch `first-draft`: `a9748fe`, `9bd0fe5`, `116d8d2`. Clean-copy check passed (229 tests, server starts). PR #1 into `master` for the review. **C10 now ends with merging PR #1, not a push to `master`** |
| Review 1 | B, C | `/code-review` on PR #1 (builder ran it, ~00:45; fixes done by 01:06) | Push 1 | ☑ 15 findings, all checked and real; 12 fixed with a failing test first, 3 deferred (#11, #14, #15). Django **240**, AI **96**, rehearsal passed, code zip re-packed (07:03 UTC = 01:03 Chicago; re-pack again after committing). Table in `docs/system-map.md`, "Code review, 18 Nov". **Fixes not committed yet: ask the builder** |
| Sync 1 | — | The room zip has arrived | B3 | ☑ 18 Nov, morning. **Finding: the floor finder took the bed top as the floor.** `floor_height` keeps the fullest 1 cm slice; the bed top (0.71 m up, flat) beat the real floor 3,471 to 3,351 points because the real floor is spread over several slices by a 2° lean of "up" (the facing-direction bias). Cameras sit 0.62 m above the false floor, 1.29 m above the real one. **Builder chose option 1 (08:10). Done by ~08:30:** the floor is now the lowest flat layer, levelled by its own plane (RANSAC, within 15° of the phone's up); `python -m roompipe relevel` corrects a built room with no GPU. AI tests **109**, rehearsal passed, code zip re-packed. The room is re-levelled into `room-20261118-1342-relevelled` beside the zip in Downloads: the floor was 1.92° off level and 0.656 m down; the cameras are now at 1.15–1.4 m; the app's import check accepts it. **Not committed yet.** Next: the builder uploads the video as a scan, then C6 imports the re-levelled folder |
| C6 | C | The `import_room` management command | Sync 1 | ◐ 18 Nov, ~00:15. Built against the demo room before Sync 1: 21 tests (suite **216**); demo zip imported on a scratch copy. New: `Scan.room_info` + migration `0004` (applied to the builder's db), `.ply` ending, `rooms/roomfolder.py`, `*.ply`/`*.zip` in `.gitignore`. System map piece 8. **☑ Real room imported 18 Nov, ~08:35:** scan 1 (place "Octave Room", the builder's test account) ← `room-20261118-1342-relevelled`: "393,033 points, in a box 4.50 x 4.10 m across and 2.78 m high" (box not wall-aligned, so larger than the room). Fix commit `2aa57d4` pushed to `first-draft`; zip re-packed clean from it |
| C7 | C | The 3D viewer page inside the app | C6 | ◐ 18 Nov, ~00:20. `/scans/<pk>/room/` + `/scans/<pk>/points.ply` (owner-checked), place-page link, pins as JSON and dots, tap shows the photo; admin Scans list shows "Id". 12 + 1 tests (suite **229**). Seen in Chromium with the made-up demo room at desktop and 390 px. System map piece 9. **Real room served, 18 Nov ~08:35** (test client as the owner: page 200, no made-up notice; `points.ply` 200, 5,895,725 bytes; logged out → 302). **Left: look at it in a browser (no screenshot in git without asking)** |
| C8 | C | The AI section filled in with the run's real numbers | Sync 1 | ☑ 18 Nov, ~09:00. `FIRST_DRAFT.md` §2 Evidence: run facts, the bed-as-floor bug and its fix, size against the builder's tape (walls −11%, bed height −9%; ceiling and bed length not measurable), wall doubling, placement 0 of 2 (anchors 1.16 m). Feature rows 1–2 and roadmap rows updated. **Open: is the corridor's long wall really at 13° to the others?** (asked) |
| C9 | C | If there is time: the experiment's AI placements shown as dots | C7 | ✗ Not possible: the run pinned 0 of 2 photos (18 Nov). Dropped, as the cut list allows |
| D1 | C | The Dollhouse look (builder's request, 18 Nov): design `docs/design/2026-11-18-dollhouse-site.md`, plan `docs/plans/2026-11-18-dollhouse-site.md` | — | ☑ 18 Nov, ~11:50. All 12 tasks built; Django **276**, Node 5; browser pass on a copy of the data. Hand placement works. **Not committed.** System map piece 10 |
| B6 | B, with C | One walk-through of the whole app, run by the builder | C1, C7 | ☐ |
| B7 | B | Review `FIRST_DRAFT.md` and `README.md`; say "commit and push" | C2 to C8 | ☐ |
| C10 | C | Final checks, the clean-copy check, commit by path, push | B7 | ☐ |
| B8 | B | Give the instructor access; submit the URL on Canvas | C10, B5 | ☐ |

## Where things stand (17 Nov 2026, about 11:45 PM)

**Built:**
- **Django:** chunk 1 (accounts) is committed. Chunks 2, 3 and 4 (the four models, the places pages, room video upload) were applied from `prebuilt/` on 17 Nov and are not committed. 123 Django tests pass.
- **AI:** the Colab notebook `ai/build_room_colab.ipynb` was reviewed against MapAnything's source on 17 Nov and fixed. The fix: fp16 on a T4, a `PRECISION` setting, a stop when the output is not real numbers, an OpenCV check, and an "are the frames upright?" check. 91 AI tests pass. `python ai/rehearse_notebook.py <folder>` runs every cell with the stand-in model, and it passed.
- **It has never run on a GPU or a real video.**
- **Code zip:** `ai/dist/memory-room-ai.zip` was packed at 05:38 UTC on 18 Nov (11:38 PM on 17 Nov in Chicago), from commit `b2580d4` plus the uncommitted changes. Re-pack it if anything in `ai/roompipe` or `ai/roomgeom` changes before the run.

**Not built:** photo upload (chunk 5, a tested kit waiting in `prebuilt/`); the 3D viewer page (a component in `prebuilt/viewer`, shown only a made-up room); importing a built room into the app; the README; the first-draft write-ups.

**Documents written on 17 Nov:**
- `docs/features.md`: the product record (built, planned, set aside, decisions, open questions).
- `docs/filming-guide.md`: how to film.
- This file.

**Git:**
- Branch `master`. The last commit, `b2580d4`, is pushed and tagged `first-push`.
- Everything listed by `git status` since then is uncommitted, including `.gitignore`, which now ignores `ai/dist/`.
- The repository on GitHub is **private**.

**Not yet done with the builder:** the walk-throughs of chunks 1 to 4 (replaced by one combined walk-through, step B6), and reading out Claude's calls for chunks 2 to 4 (`docs/system-map.md` lists them).

## Already decided: do not reopen

All of these are in `docs/features.md` ("Product decisions") or `docs/system-map.md`.

| Decision | By, when |
| --- | --- |
| Memory Room replaces Clearance (the P2-A2 idea) | Builder, 16 Nov |
| Target users: anyone who wants to keep the memories of a place | Builder, 17 Nov |
| Core features: 1 Capture, 2 Memory map, **3 Versions over time** | Builder, 17 Nov |
| Search and a timeline are the class's data feature | Builder, 17 Nov |
| Photos show as dots for now | Builder, 17 Nov |
| Photos the AI can't place are highlighted; the user places them; the app refines the spot later | Builder, 17 Nov (refinement: discuss after the draft) |
| One room for now; growing a place with more recordings later | Builder, 17 Nov |
| Gallery search after 18 Nov; sharing wanted, designed later | Builder, 17 Nov |
| **D2 = a**: many photos at once | Builder, 17 Nov |
| **D3 = a**: photo files only through the owner check | Builder, 17 Nov |
| The viewer reads **PLY** | Builder, 17 Nov |
| A built room reaches the app through a **management command** run on the downloaded room folder | Builder, 17 Nov |
| Film in portrait, FHD at 30 frames a second | Recommended 17 Nov; in the filming guide |
| A separate Pin model (memory, scan, x, y, z); our own User class (D1) | Builder, 16 Nov |
| Apache weights only; SQLite and local disk until deployment; Claude writes the code until the first draft is in | Builder, 16 Nov |
| `CLAUDE.md` is never committed; Claude is never a contributor; `docs/` is pushed | Builder, 16 and 17 Nov |

## What the first draft must contain, and where each part will be

| Requirement (points) | What it asks | Where it will be | Status |
| --- | --- | --- | --- |
| 1. Updated product scope (15) | One page: the idea, the problem, target users, three core features, changes since P2-A2 | `FIRST_DRAFT.md` §1 (C2) | ☐ |
| 2. Functional Django foundation (40) | A project and app; two or more models with a relationship; views and templates; a form; one database-backed workflow | The app. **Already met by chunks 1 to 4.** Chunk 5, the import and the viewer add to it | Met; more coming |
| 3. Initial AI implementation or plan (20) | The model or technique; input and output; how it works with Django; evidence of experimentation | `FIRST_DRAFT.md` §2 (C4, C8), the notebook, `ai/`, the run's record | ☐ |
| 4. Progress and roadmap (15) | The six-row table: task, status, responsible member, expected completion | `FIRST_DRAFT.md` §3 (C3) | ☐ |
| 5. GitHub and reproducibility (10) | Code pushed; a README that explains how to run the prototype; the instructor can open the repository | `README.md` (C5), push (C10), access (B5, B8) | ☐ |

`FIRST_DRAFT.md` sits at the repository root, so it is the first thing the instructor sees, and `README.md` links to it. That location is Claude's call; the builder may move it.

## Suggested timing for Wednesday

| When | Builder | Claude |
| --- | --- | --- |
| Morning, by about 11 AM | B0; B1 (about 20 min with measuring); B2 (start the notebook: about 5 min to install, then the weights download, then the build); B4; B5 | C1 (about 1 hour), then C2, C3, C4 drafts |
| Midday | B3 when Colab finishes | C5; then C6 and C7 when the zip arrives |
| Afternoon, about 3 to 5 PM | B6 (about 45 min) | C8; C9 if there is time |
| About 6 to 7 PM | **Building stops** (design §7). B7: review | Fixes from the review |
| About 8 to 9 PM | Says "commit and push" | C10 |
| Before 11:59 PM | B8 | — |

## The builder's steps

**B0. Where the model runs.**
- Recommended: Colab. The laptop's RTX 4050 is not usable today (see "The laptop GPU" below).
- If the builder still wants the laptop, stop and plan that first. It is a half-day job with unknowns.

**B1. Film, photograph, measure.**
- Follow `docs/filming-guide.md`: five numbered paper sheets on the floor, then the video in portrait at FHD 30 fps on the 1× lens, then five photos standing on the sheets, then five old photos.
- Also **measure the room with a tape**: length, width and ceiling height, in metres. Write them down. They are the check on the model's sense of scale in C8.

**B2. Drive and Colab.**
- In the Drive app, on Wi-Fi, create `MyDrive/MemoryRoom/`. Put the video in it, and the ten photos in `MyDrive/MemoryRoom/photos/`.
- From the laptop, upload `ai/dist/memory-room-ai.zip` into the same folder.
- In Colab: File → Upload notebook → `ai/build_room_colab.ipynb`.
- Runtime → Change runtime type → T4 GPU, then Runtime → Run all. Allow Drive access when asked.
- Watch two pictures:
  - **The frames sheet (section 6):** are the frames upright and sharp? If they are sideways, stop.
  - **The preview (section 9):** does it look like the room?
- If anything stops, see "If something goes wrong".

**B3. Bring the results to the laptop.**
- Download `MyDrive/MemoryRoom/rooms/<run name>.zip` to **Downloads**. It must not go inside the project folder: it shows the room.
- Tell Claude the path.
- Copy the room video to the laptop too: it gets uploaded into the app as the room's scan before C6.

**B4. One sentence for the scope page:** why Memory Room replaced Clearance.

**B5. Repository access.**
- The repository is private, and the brief says the instructor must be able to open it.
- Choose one: add the instructor as a collaborator (GitHub → Settings → Collaborators; this needs their GitHub username), or make the repository public.
- Check Canvas for the course's preference.

**B6. The walk-through.** About 45 minutes, with Claude. This replaces the four walk-throughs owed for chunks 1 to 4 and the one for chunk 5; the full versions can be done after the draft.
- Run `.venv\Scripts\python.exe manage.py runserver` and sign up.
- Create a place, upload the real room video, and add several photos at once.
- Open a photo. Then log out and try the photo's address. Then try it from a second account, which should get a 404.
- Run the import command on the real room zip, then open the 3D room.
- Claude traces one request (the photo upload) through the code while you watch it happen.

**B7. Review.**
- Read `FIRST_DRAFT.md` and `README.md`, and check the roadmap dates.
- Read the list of calls Claude made during the day.
- Then say "commit and push".

**B8. Hand in.**
- Give the instructor access as chosen in B5.
- Submit `https://github.com/Revaant-D/Memory-Room` on Canvas.
- Open the URL in a private browser window to confirm what a logged-out visitor sees (a 404 is expected while the repository is private).

## Claude's steps

### C1. Chunk 5: photos, from the D2a-D3a kit

**D2 and D3 are already answered (a and a, the builder, 17 Nov).** `prebuilt/README.md` says to put them to the builder before applying chunk 5; that has been done, so don't ask again. Go straight to the steps below.

1. **Read first:**
   - `prebuilt/README.md`: the "how to apply" sections and the note "Chunk 5 is two applies".
   - `prebuilt/django/chunk5-rest/README.md`.
   - The chunk 5 part of `docs/plans/2026-11-16-django-foundation.md` (from "## Decide" above Task 10 through "## Record (chunk 5)").
2. **Check:** run `.venv\Scripts\python.exe prebuilt\tools\kit.py status`. Chunks 2 to 4 should show as applied; `chunk5-parts` and `chunk5-D2a-D3a` should be ready. If anything says BLOCKED, read that kit's "If it no longer fits" section. Do not rebuild the kit.
3. **Verify:** `kit.py verify --choice chunk5-D2a-D3a`. Every line must end `ok`.
4. **Apply:**
   - `kit.py apply chunk5-parts`, read what it would do, then `kit.py apply chunk5-parts --write`.
   - The same for `chunk5-D2a-D3a`.
5. **Test:**
   - `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`, then `migrate`, then `manage.py test`.
   - Write the real test count in the Status table.
6. **Real check:**
   - Start the server and add three photos at once to a place.
   - Open one. A logged-out visitor is sent to log in; another user gets a 404.
7. **Record:**
   - Add a "Photos" piece to `docs/system-map.md`, based on `prebuilt/django/chunk5-rest/system-map-section.md` and set to D2a/D3a. Mark D2 and D3 as **the builder's decisions, 17 Nov**.
   - Update the plan's status table (row 5) with an "As built" note, update `CLAUDE.md`, and move photos to "Built" in `docs/features.md`.
8. **List the plan's calls for chunk 5 for the builder:**
   - JPEG, PNG and WebP only.
   - At most 20 MB per photo and 50 photos per upload.
   - HEIC is refused with a message.
   - One bad file stops the whole batch.
   - The date is read from inside the photo.

**Done when:** every test passes and the real check passes.

### C2. `FIRST_DRAFT.md` §1: product scope (at most one page)

Sources: `docs/features.md`, `docs/reference/05-I-M2-memory-room.md` §5 (competitors), and `docs/Clearance_Project_Idea_Description (older idea).pdf`.

- **Name:** Memory Room. **Problem**, in two or three sentences. The Popsa figure, if used, is a vendor survey reported second-hand; say so.
- **Target users:** anyone who wants to keep the memories of a place, with examples: a first apartment, a dorm room, a family home before a sale.
- **Value:** "the room is the index": a way back into a pile of photos.
- **Three core features:** Capture, Memory map, Versions over time. Say plainly which parts work today.
- **How it differs**, in a few lines:
  - GausNote pins notes and photos by hand, on an iPad, in a scan made by another app.
  - Scaniverse and Polycam make bare scans.
  - Multi Splat and TimeSplat step through versions but hold no photos.
  - Photosynth retired in 2017.
  - The gap Memory Room fills: the photos you already have, placed automatically, in a browser on any phone, inside versions of the place.
- **Changes since P2-A2:**
  - Clearance (does furniture fit before you buy) became Memory Room.
  - Kept: a phone video becomes a metric 3D room through MapAnything; Django; three.js.
  - Dropped: the browser extension, the fit editor, the clearance checks, furniture detection, ARCore camera tracking.
  - Why: the builder's sentence from B4. Link the PDF.

### C3. `FIRST_DRAFT.md` §3: progress and roadmap

The brief's table with exactly its six rows: Django Core Features, Database and APIs, AI Integration, Evaluation and Testing, Deployment, Documentation. Columns: task, current status, responsible member (**Revaant Daga, solo**), expected completion.

- **Status:** from the facts at the time of writing, with real test counts.
- **Dates:** a proposal the builder confirms in B7. They follow the idea write-up's three weeks:

| Area | Remaining work | Proposed date |
| --- | --- | --- |
| Django core | Viewer page (first version 18 Nov); versions pages | 2 Dec |
| Database and APIs | JSON API (a room with its pins; move a pin) | 29 Nov |
| Database and APIs | Search and timeline (the data feature) | 1 Dec |
| AI | Django starts the GPU job | 29 Nov |
| AI | Placement with highlighted photos and hand placement | 3 Dec |
| AI | Refining a hand-placed photo; lining up two scans | 5 Dec |
| Evaluation | Five realistic tests, two failures, one improvement | 5 Dec |
| Deployment | Live host, GPU service, cost comparison, 10,000-user estimate | 6 Dec |
| Documentation | `README_AI.md` and the three-minute video | 8 Dec |

Add a short "Next after the draft" list from "Planned for the final" in `docs/features.md`.

### C4. `FIRST_DRAFT.md` §2: the AI plan, before the run

- **The AI features:** the table from `docs/features.md`, numbered 1 to 5, saying which exist.
- **Model:**
  - MapAnything (Meta and Carnegie Mellon, 2025), Apache-2.0 weights `facebook/map-anything-apache` at revision `00f9c24`, code at commit `3d10cf7`.
  - **Why this model:** metric 3D from ordinary images, a camera for every image, one pass with no training per room, and a licence that allows commercial use.
  - **Alternatives considered:**
    - classic photogrammetry: slow, and fails on blank walls
    - Gaussian splats: training per room; a later upgrade
    - a depth sensor: needs a native app and a LiDAR phone
    - VGGT: its commercial weights are behind a request form
    - Depth Anything 3
  - **Feasibility points:** GPU memory; fp16 on a T4; why the room is filmed in portrait.
- **Input and output:**
  - Building the room: video → 60 sharpest frames → model → a 3D point for each pixel and a camera for each frame → a levelled, thinned PLY file, the cameras and 20 anchor frames.
  - Placing photos: photos plus 10 anchors → model, twice → a position, and whether the two answers agree → pin, or ask the user.
- **How it works with Django:**
  - Now: the phone uploads the video as a Scan → the Colab notebook → the room zip → `import_room` → `Scan.points_file`, status "ready" → the viewer page.
  - By 8 Dec: a Django view starts the GPU job. The proposal is Modal, with Django polling for the result instead of waiting to be called back. The result goes through the same import code. Placements become Pin rows with `placed_by = "ai"`.
- **Reliability already built:**
  - only the Apache weights load
  - unreadable images are counted, not silently skipped
  - a tilted video or no visible floor means "film again"
  - out of memory means a retry with fewer frames
  - invalid numbers stop the run and name the fix
  - GPS and EXIF are stripped from photo copies
  - `run.json` records every run, failures included
- **Evidence:** a placeholder that C8 fills.

### C5. `README.md`

Follow the plan's "Task 13: README and the clean-copy check". Content:
- What the app is, and its first-draft status (what works, what doesn't yet). Link `FIRST_DRAFT.md`.
- Setup, in PowerShell and in a Unix shell: `python -m venv .venv`, `pip install -r requirements.txt`, `manage.py migrate`, optionally `createsuperuser`, `runserver`.
- Environment variables: `DJANGO_SECRET_KEY` (optional; a key file is made on first run), `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`.
- How to run the tests.
- How to reach the AI: `ai/README.md` for the notebook, then `import_room`.
- A map of the repository, and where the docs are.

The clean-copy check itself is in C10, because it needs a commit.

### C6. The `import_room` command

`.venv\Scripts\python.exe manage.py import_room <scan id> <room folder or .zip>`

**What it does:**
- Reads `room.json` and requires `version: 1` and a `points.ply`.
- Copies `points.ply` into `Scan.points_file`. Change the stored file ending in `rooms/models.py` from `-points.bin` to `-points.ply`. No migration is needed: the function keeps its name.
- Keeps what the viewer needs. **Proposed call, to list for the builder:** one new field, `Scan.room_info` (a JSONField), holding the box, point count, up consistency, frames used, weights revision and precision. Design §6 said `n_points` and `room_box` would arrive with the viewer. Needs migration `0004`.
- Sets the status to "ready".

**What it refuses, with a plain message:**
- an unknown scan
- a missing file
- a room made by the stand-in model (`run.json` has `"stand_in": true`), unless `--made-up` is given. With `--made-up` it stores `made_up: true`, and the viewer page then shows a "MADE-UP ROOM" notice. This keeps a fake room from ever being shown as a result.

**Also:**
- Room data lives only in `media/`, which is never committed.
- Tests: use a small room folder made with `roompipe`'s demo (`python -m roompipe demo`, run from `ai/` with the AI test Python), or a tiny hand-written PLY.
- Record it in `docs/system-map.md` and `docs/features.md`.

### C7. The viewer page

- Read `prebuilt/viewer/README.md`, especially the section on putting it in the app.
- Copy `roomviewer.js`, `loaders.js` and `vendor/` (three.js 0.170.0, MIT) into `static/viewer/`. Load the PLY only.
- **Addresses:**
  - `/scans/<pk>/room/`: the page.
  - `/scans/<pk>/points.ply`: the file, served through `get_own_scan` like the private photo view (D3a).
  - On the place's page, a "View the room in 3D" link when a scan is ready.
- Pins go to the page as JSON with `json_script` and are drawn as dots. This is the start of the JSON API.
- **Tests:** the owner check on both addresses (another user gets a 404; a logged-out visitor is sent to log in); the file comes back with the right type; a made-up room shows its notice.
- **Look at it in a real browser** with the real room (Playwright is available). A screenshot shows the inside of the builder's room. Ask before putting any picture of it in the repository.
- Record it in `docs/system-map.md`.

### C8. The AI section, with real numbers

Fill §2's "Evidence" from the zip's `run.json`, `room.json` and `placements.json`, plus the builder's tape measurements:
- the GPU, precision used, frames used and attempts, seconds per step and peak GPU memory
- the point count, and the room's box against the measured room (say that without wall alignment the box is larger than the room)
- the up consistency
- for the photos: how many were pinned and how many were "ask", the gaps between the two tries, and how close each "today" photo landed to its paper sheet, judged on `preview-photos.png`
- **what failed, said plainly**

This is also row 1 of the final's evaluation table, so start that table here. Real results only: if the run failed, the failure and its error from `run.json` are the evidence.

### C9. If there is time: AI placements as dots

**Recommended for the draft, with no new code:**
1. The builder uploads the same ten photos as memories.
2. Claude creates Pin rows in the admin for the photos the notebook pinned, using x, y, z from `placements.json` and `placed_by = "ai"`. These are real model outputs entered by hand; the write-up says so.

Automating this means `import_room` has to know which memory each photo is, and it doesn't; that waits for 8 Dec.

### C10. Final checks and the push (only after the builder's "commit and push")

1. Run `.venv\Scripts\python.exe manage.py check`, then `manage.py test`.
2. Run the AI tests and the rehearsal (see "Rules that bite" for the AI test Python). Write down the counts.
3. **Before staging:**
   - `git check-ignore CLAUDE.md` must print `CLAUDE.md`. If it prints nothing, add `CLAUDE.md` and `.claude/` to `.git/info/exclude`.
   - `git status --short`.
4. **Add files by path only** (never `git add .` or `-A`): the changed app files, the migrations, `docs/` (including `features.md`, `filming-guide.md`, the Clearance PDF and this file), `ai/` (not `ai/dist/`), `FIRST_DRAFT.md`, `README.md`, `.gitignore`.
   **Never add:** `CLAUDE.md`, `.claude/`, `db.sqlite3`, `.secret_key`, `media/`, `ai/dist/`, any room folder or zip, any video or photo.
5. **Commit** with a message that mentions no AI tool. Then `git log -1 --format="%an | %cn | [%(trailers)]"` must show the builder's name twice and empty brackets.
6. **Clean-copy check** (plan Task 13):
   - `git clone . "$env:TEMP\mr-clean"`, then make a new venv in it with `py -3.14 -m venv`.
   - `pip install -r requirements.txt`, `migrate`, `test`, then start `runserver` and stop it.
   - If anything fails, fix it with a new commit and repeat.
7. `git push origin master`. Tick C10 with the commit hash.

## If something goes wrong

| What happens | Do this |
| --- | --- |
| Colab gives no GPU | Try again in 30 to 60 minutes; free GPUs come and go. If there is still none by about 2 PM: the AI section reports the attempt, and the viewer shows the made-up demo room imported with `--made-up`, labelled as made up. Don't switch to the laptop GPU today |
| "No GPU" when Run all starts | Runtime → Change runtime type → T4 GPU → Save, then Run all |
| The install asks for a restart | Runtime → Restart session, then Run all. The install is skipped the second time |
| "OpenCV does not load after the install" | Run the command the message gives, restart the session, Run all |
| Out of memory even at 30 frames | `run.json` records it. It is a result: write it up. After the draft, try a bigger GPU (Modal L4, about $0.80 an hour) |
| "not real numbers" | Set `PRECISION = "fp32"` in section 1 and Run all again |
| "could not be levelled" | Film again: phone upright, floor in view (filming guide) |
| The room comes out tilted (in `preview.png`'s side view the floor slopes or is a thick band) | `estimate_up` (`ai/roomgeom/level.py`) averages each frame's "down", so a down-tilted phone leans the room toward whichever way it faced most. A loop cancels this; the builder's tight room may not. The agreement score does not catch it. Film again, facing each way for about the same time, or (the builder's call) make `estimate_up` use the frames' left-right axes, which pitch does not affect |
| The frames are sideways on the sheet | Stop. Re-save the video from the phone's gallery, or film again |
| The room looks rough or wrong | Still a result. Note what is wrong (bent floor, doubled walls, scale against the tape) and show it as it is |
| Placement pins nothing, or pins wrongly | A result. Report the counts and how far off the photos landed; hand placement is planned for 8 Dec |
| A chunk 5 kit says BLOCKED | Read its "If it no longer fits"; don't rebuild. Photos are not needed for the rubric's minimum |
| The Claude plan hits its usage limit | This file and `CLAUDE.md` are the handoff. A new session starts at the first unticked C step |

## If time runs short: drop in this order

1. C9 (AI dots).
2. Extras in C7 beyond showing the room.
3. C7 and C6 (the import and the viewer). §2 then relies on `run.json` and the notebook's pictures. Pictures of the room go in only if the builder agrees.
4. C1 (photos). Chunks 1 to 4 already meet requirement 2.
5. B6 shortened to sign-up, a place, a video upload and one trace.

**Never drop:** C2, C3, C4 with C8 (or the documented failure), C5, C10, B8.

## Rules that bite in this project

- **Django:** always `.venv\Scripts\python.exe manage.py ...`. This machine has several Pythons.
- **AI tests:** they use their own Python, outside the project, which needs numpy, OpenCV, Pillow, matplotlib and IPython. If it is gone, recreate it:
  `py -3.14 -m venv "$env:TEMP\ai-venv"; & "$env:TEMP\ai-venv\Scripts\python.exe" -m pip install -r ai\requirements.txt`
  Then, from `ai/`: `& "$env:TEMP\ai-venv\Scripts\python.exe" -m unittest discover -s tests` (91 tests on 17 Nov).
  The rehearsal, from the project root: `& "$env:TEMP\ai-venv\Scripts\python.exe" ai\rehearse_notebook.py <empty folder>`, after `python ai\pack_for_colab.py`.
- **PowerShell 5.1:** no `&&`; use `;` or `if ($?) { }`.
- **Git:** `CLAUDE.md` is never committed. No co-author lines or AI mentions in commits. Add files by path. Commit and push only on the builder's word.
- **AI and data:** load only `facebook/map-anything-apache`. Report real results only. A made-up room is always labelled as made up. Nothing showing the inside of the builder's room goes into git without asking.

## The laptop GPU (RTX 4050), checked 17 Nov

- **Windows does not see a working NVIDIA GPU.** The second display adapter is the NVIDIA card, running on Windows' basic display driver in an error state (`CM_PROB_FAILED_START`), and `nvidia-smi` is not installed. So the NVIDIA driver is missing or failing. Some laptops also have a maker's setting ("Eco" or "iGPU only") that keeps the NVIDIA GPU off.
- **Memory:**
  - The RTX 4050 Laptop GPU has 6 GB of video memory. That is NVIDIA's specification, not read from this machine, because the driver isn't running.
  - The model's weights are 4.91 GB (`model.safetensors`). In full precision that leaves about 1 GB for the work on 60 frames, so the room build will very likely run out of memory. Colab's T4 has 16 GB.
  - The laptop has 15.3 GB of RAM, with 0.3 GB free at the time of the check; loading the model needs about 5 GB free.
- **To use it** would take:
  - installing the NVIDIA driver and possibly changing the maker's GPU mode
  - installing PyTorch with CUDA (several GB) and MapAnything on Windows, which has never been tried here
  - closing applications
  - very likely running with fewer frames, or with the weights cast to bf16, which MapAnything doesn't document
- **Verdict:** Colab for the first draft. After the draft, the laptop is worth a test for placing photos (20 images or fewer). It also matters for the final, because the brief allows "a reproducible local deployment with a clear technical justification".

## After the first draft

Next is the "Planned for the final submission (8 Dec)" table in `docs/features.md`, in the order of the roadmap (C3). Open questions to bring to the builder are listed there too: sharing and export, refining hand-placed photos, how a scan that extends a place differs from a version, and whether a rented GPU counts as deployment.
