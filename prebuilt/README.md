# prebuilt/ : work done ahead, waiting for the builder

**Read this first if you are a new Claude session.** Then read `CLAUDE.md` as usual.

## What this folder is

On 16 Nov 2026 the builder had model credits that were about to expire and had not yet gone through the system guide. They asked for the parts of the app that are unlikely to change to be built ahead of time, kept apart from the running app, so that later sessions can put them in quickly and cheaply.

Everything here is **finished and tested, but not part of the app**. Django never imports this folder, the test runner does not look inside it, and nothing here is committed.

The project's rule "don't build a component before its decisions are made" still holds. Only two kinds of thing were built here:

- pieces whose decisions the builder had already made (the data model, 16 Nov), or that the build plan lists with no builder decision (plan chunks 3 and 4);
- pieces with no product decision in them at all (the geometry maths, the steps around the model, and the viewer the approved design already calls for), built so that every decision still open stays open.

Chunk 5 (photos) has two decisions that are the builder's and were still open: D2 and D3. It is here in a form that leaves them open: `django/chunk5-parts` holds the pieces that come out the same under every answer, and `django/chunk5-rest` holds the remainder **four times over**, once per combination of answers, all tested to the same standard. Nothing about chunk 5 is to be applied until the builder has answered both.

## What is in it

All were finished on 16 Nov 2026. The test numbers are what the test runner printed that day.

| Name | Feeds | Tests | Stops fitting if... |
| --- | --- | --- | --- |
| `django/chunk2-models` | Plan chunk 2 (Tasks 3, 4, 5): the four models | 78 pass (50 from chunk 1 + 28) | the builder changes a field or rule in §6 of the design |
| `django/chunk3-places` | Plan chunk 3 (Tasks 6, 7): places pages | 99 pass (+21) | the builder overrules one of chunk 3's calls |
| `django/chunk4-video` | Plan chunk 4 (Tasks 8, 9): room video upload | 123 pass (+24) | the builder changes the video limits (one setting; see its README) |
| `django/chunk5-parts` | Part of plan chunk 5 (Task 10): photo date, photo check, caption form | 143 pass (+20) | never; it holds only what D2 and D3 do not affect |
| `django/chunk5-rest` (four versions) | The rest of plan chunk 5 (Tasks 10, 11, 12): adding photos, the grid, a photo's page, fetching the file | 195 or 192 pass, depending on the version (+52 or +49) | the builder wants something that is none of the four; see its README |
| `ai/geometry` | The later AI work (no plan yet): levelling, the anchor fit, the pin-or-ask check, and the points file in both candidate formats | 37 pass, on made-up data, separate from Django | the builder drops the anchor-fit placement method (part of it survives; see its README) |
| `ai/pipeline` | The same AI work: picking frames, the model call, building a room folder, placing photos; plus a stand-in model and a made-up demo room | 25 pass with the stand-in model. **The one file that calls the real model has never been run** | the builder changes the placement method; the build half is unaffected |
| `viewer` | The viewer page (design §7): coloured points in three.js, pins, tap to choose, tap to place | No test suite. Checked by script in a real browser against the made-up room; see its README for the list | the builder chooses a look other than coloured points |

**Chunks or components?** Both, on purpose. `chunk2`, `chunk3` and `chunk4` are **chunks**: each is exactly one chunk of `docs/plans/2026-11-16-django-foundation.md`, cut where the plan cuts, so the plan's Decide, Walk through and Record steps apply unchanged. `chunk5-parts` plus one version of `chunk5-rest` together make chunk 5. `ai/geometry`, `ai/pipeline` and `viewer` are **components**: parts that later work will pick up and build around. No plan exists yet for the work they feed, so they have no chunk to belong to.

Each Django count is the whole suite with that kit and every kit above it laid on the project. The real project, with nothing applied, still has its own 50 tests; that was re-run after this folder was made.

```
prebuilt/
├─ README.md            this file
├─ kits.json            the four Django kits in order, and the four chunk 5 versions
├─ tools/kit.py         status / verify / apply / plan-tests
├─ tools/breakcheck.py  breaks the code on purpose to prove the tests notice
├─ django/
│  ├─ chunk2-models/    README.md, manifest.json, system-map-section.md, files/
│  ├─ chunk3-places/    the same four things
│  ├─ chunk4-video/     the same four things
│  ├─ chunk5-parts/     README.md, manifest.json, files/
│  └─ chunk5-rest/      README.md, system-map-section.md, and four folders:
│                       D2a-D3a/  D2b-D3a/  D2a-D3b/  D2b-D3b/   (each: manifest.json, files/)
├─ ai/
│  ├─ geometry/         README.md, the roomgeom package, tests/, requirements.txt (not a kit)
│  └─ pipeline/         README.md, the roompipe package, tests/ (not a kit)
└─ viewer/              README.md, roomviewer.js, loaders.js, demo.html, demo/ (a made-up room), vendor/ (three.js)
```

Inside each kit, `files/` mirrors the project's layout. `files/rooms/models.py` is the whole of `rooms/models.py` as it should be after that chunk. Kits are cumulative: chunk 3's files assume chunk 2 is in.

## How to use a kit (for the session that applies it)

Each kit replaces the **Build** step of its chunk and nothing else. The builder's loop in `CLAUDE.md` still runs in full.

1. **Orient.** Read `CLAUDE.md`, the chunk in the plan, and the kit's `README.md`. Then:

   ```powershell
   .venv\Scripts\python.exe manage.py test
   .venv\Scripts\python.exe prebuilt\tools\kit.py status
   .venv\Scripts\python.exe prebuilt\tools\kit.py verify --upto chunk2-models
   ```

   `status` must say READY for the kit. `verify` lays the kits on a temporary copy of the project and runs the checks and tests there; it must end with every line `ok`. If either fails, the project has moved since the kit was made: stop, read the kit's README section "If it no longer fits", and tell the builder.

2. **Decide.** Read out the chunk's "Claude's calls" from the plan, **and** the extra calls listed in the kit's README, so the builder can overrule any of them before the code goes in. If the builder overrules one, change the kit's files first (the README says where), re-run `verify`, then go on.

3. **Build** (this is the step the kit shortens):

   ```powershell
   .venv\Scripts\python.exe prebuilt\tools\kit.py apply chunk2-models          # shows what it would do
   .venv\Scripts\python.exe prebuilt\tools\kit.py apply chunk2-models --write  # copies the files
   .venv\Scripts\python.exe manage.py migrate
   .venv\Scripts\python.exe manage.py test
   ```

   The test count must match the kit's README. Report the real number.

4. **Walk through.** Do the chunk's walk-through from the plan with the builder. This step is the reason the builder asked for the loop; do not skip it because the code arrived quickly.

5. **Record.** Each kit has a `system-map-section.md`: a draft of the section the plan asks for. Check it against what was actually applied, then add it to `docs/system-map.md`. Tick the chunk in the plan's table, add a short "As built" note there saying the code came from this folder, and update "Where things stand" in `CLAUDE.md`.

6. **Commit only if the builder asks**, following the two git rules in `CLAUDE.md` (add by path; `CLAUDE.md` never committed; no mention of Claude in the commit). After a kit is applied and committed, its folder here can be deleted.

`apply` refuses to copy anything if a project file it would replace is not the file the kit was built against. That is the safety net against the project having changed. It never migrates, commits or deletes.

**Doing several chunks in one sitting** is the builder's call, not the session's. The kits make it cheap to apply 2, 3 and 4 back to back, but each still has its own calls to read out and its own walk-through.

**Chunk 5 is two applies.** In the chunk 5 session, put D2 and D3 to the builder exactly as the plan's Decide block does, with the plan's recommendation, and wait for the answers. Do not mention which versions exist until they have answered; all four do. Then apply `chunk5-parts`, then the one matching version (`chunk5-D2a-D3a`, `chunk5-D2b-D3a`, `chunk5-D2a-D3b` or `chunk5-D2b-D3b`). `kit.py` refuses a second version on top of the first. `django/chunk5-rest/README.md` sets out what each answer changes in the code.

**`ai/geometry`, `ai/pipeline` and `viewer`** are not applied with `kit.py` at all. A later session copies or imports them when the work they belong to is planned. Each has its own README, which says what is decided, what is still the builder's to decide, and what has and has not been run. How the three fit together:

```
room video ─► roompipe.frames ─► roompipe.model (REAL MODEL, NEVER RUN) ─► roompipe.build ─► room folder
                                                                     (uses roomgeom.level, roomgeom.pointsfile)
photos ─────► roompipe.place ─► placements.json   (uses roomgeom.fit, roomgeom.place)
room folder ─► viewer/loaders.js ─► viewer/roomviewer.js ─► the room on screen
```

Anything shown from `viewer/demo/` or made with `roompipe demo` is a **made-up room**. It must never be presented as a reconstruction or as a result; the class forbids fabricated outcomes, and the demo page carries a notice saying so.

## What a new session should not do

- Do not treat anything here as built. The plan's status table and `CLAUDE.md` say what is built; a kit only becomes "built" after it is applied, walked through and recorded.
- Do not apply a kit without the builder present, or skip the Decide step because the code already exists.
- Do not edit files under a kit's `files/` to fix something in the running app, or the other way round. One is a copy waiting to go in; the other is the app.
- Do not rebuild a kit from scratch because `status` says BLOCKED. Read the kit's "If it no longer fits" section; the differences are small and listed.

## How to check that what is here is correct

Do not take this folder's word for it. The session that built it and the session that tested it were the same session. Five checks, from quickest to most telling. The first three are commands and take under a minute together.

| # | Check | Command or action | What it proves | What it does not prove |
| --- | --- | --- | --- | --- |
| 1 | The kits still fit the project and their tests pass | `kit.py status`, then `kit.py verify`. For a chunk 5 version: `kit.py verify --choice chunk5-D2a-D3a` (or another name) | The code runs, the migrations match the models, every test passes on a fresh copy, no files leak into `media/` | That the tests are any good |
| 2 | The plan's tests are all there | `kit.py plan-tests` | Each of the 67 tests the plan names for chunks 2 to 4 exists by name | That each test checks what its name says |
| 3 | The tests can fail | `.venv\Scripts\python.exe prebuilt\tools\breakcheck.py`, and with `--choice NAME` for a chunk 5 version | With one rule broken at a time (owner check removed, files not deleted, size limit ignored, ...), the suite fails. On 16 Nov: 12 of 12 caught for the four kits; 18, 16, 17 and 15 of the same number for the four chunk 5 versions | Rules that are not on its list |
| 4 | The code says what the builder decided | Read `files/rooms/models.py` in `chunk2-models` beside §6 of the design, field by field and rule by rule. Read each kit's "Calls made here" list and confirm nothing in it contradicts the plan or `CLAUDE.md` | Agreement with the written decisions | That the pages are pleasant to use |
| 5 | A person can use it | `kit.py verify --keep` (add `--choice NAME` to include photos), then run the server from the kept copy (the command prints how) and click through: sign up, make a place, rename it, upload a short real video, delete it, try another user's address in a private window | The pages work in a real browser with real files, before anything touches the real project | Nothing; this is the check that was never done |

For `ai/geometry` and `ai/pipeline`, checks 1 and 4 have their own form: run their tests (each README says how; they need numpy, which is not in the project's `.venv`), and read `roomgeom/fit.py` and `roomgeom/place.py` beside the code sketch in the T5 technical design ("Placing a photo, and knowing when not to"). Their real test is the first run on real model output, which no session can do without a GPU. For `viewer`, serve the folder and open `demo.html` (its README says how); that takes a minute and is the whole check.

A sixth, optional check: ask a fresh session to review one kit's `files/` **before** it reads that kit's README, so its reading is not steered by this folder's own account of itself.

Known weak spots, so a checker knows where to look first:

- The tests were written alongside the code, not before it. Check 3 is the answer to that, and it covers only the rules on its list.
- Applying the kits one after another with `kit.py apply --write` was tried once, on a throwaway copy, with one chunk 5 version (`chunk5-D2b-D3b`): it applied, migrated and passed. The other three versions were verified only by laying them on a copy (`verify --choice`), not through `apply`.
- The test video is 64 bytes. Nothing has shown that a 300 MB upload works.
- Templates were only ever rendered by tests. Layout, wording and phone width are unseen.
- The `jpeg_file` date helper is checked only indirectly, through the photo-date tests in `chunk5-parts`.

## If the builder changes their mind

| If this changes | Then |
| --- | --- |
| A model field, a rule, or Pin's shape (§6) | `chunk2-models` must be edited: `files/rooms/models.py`, its tests, and the three migrations deleted and regenerated. Every later kit must be re-verified |
| The address scheme (`/places/<slug>/`) or "404, not 403" | `chunk3-places`: `access.py`, `urls.py`, and the tests that assert addresses |
| Video limits (500 MB, MP4/MOV) | `chunk4-video`: one setting and `rooms/validators.py`; see its README |
| The points-file format | Nothing here breaks. `Scan.points_file` is a plain file field; only the stored ending (`-points.bin`) in `rooms/models.py` might be renamed |
| D2 or D3, either way | Nothing here breaks. `chunk5-parts` holds what every answer shares, and `chunk5-rest` has a version for each combination |
| Function views, the test runner, the template include | Do not use the Django kits as they are; they follow chunk 1's style |

After editing any kit file, from the project folder (and only while **no** kit has been applied yet):

```powershell
.venv\Scripts\python.exe prebuilt\tools\kit.py rebuild-manifests
.venv\Scripts\python.exe prebuilt\tools\kit.py verify
```

## How this was built, and what "tested" means here

- A copy of the project at commit `4ed4bda` was cloned into a temporary folder. Each chunk was written there and its tests run there with the project's own Python. The changed files were then copied into the kit. The real `accounts/`, `rooms/`, `config/`, `templates/` and `static/` folders were never edited.
- The tests were written alongside the code, not strictly before it as the plan asks. Every test listed in the plan for these chunks exists and was seen to pass. Test counts in this folder are numbers that were actually printed by the test runner on 16 Nov 2026.
- Nothing was run in a browser. The walk-throughs will be the first time a person clicks through these pages.
- The geometry library and the pipeline were tested only on made-up data with known answers. Neither has seen output from the real reconstruction model, and `roompipe/model.py`, the one file that calls it, has never been run. numpy is not in the project's `.venv`; these tests ran in a throwaway environment (Python 3.14.3, numpy 2.5.5, opencv 5.0.0).
- The viewer was driven by a script in Chromium on this computer. It has not been opened on a phone or in another browser.
- `viewer/vendor/` holds three.js 0.170.0, downloaded unmodified from unpkg.com. It is the only third-party code in this folder.
- No real video and no real phone photo has been through any of this code.
- The temporary folder used for building is gone or will be; nothing in this folder depends on it. `kit.py verify` rebuilds the same check from scratch whenever it is run.

## Git

This folder is untracked. It is not in `.gitignore`, so it will show up in `git status`. Whether it is ever committed is the builder's choice; the plan's rule of adding files by path means it will not be swept in by accident. Like `docs/`, the text in this folder names Claude, which matters for the open question about what is pushed to GitHub.
