# Memory Room: features, plans and ideas

This file records what is built, what is planned, what is set aside for later, and the product decisions behind them. Read it when you want to know what Memory Room does, where an idea went, or what to build next. For how a built piece works, see `docs/system-map.md`.

Update it whenever something is built, decided or set aside.

**Last updated:** 18 Nov 2026 (photos built).

## The product, as of 17 Nov 2026

Film a place you have memories in, once, on your phone. It becomes a 3D room you can turn and zoom around. Your photos from that place show up as dots at the spots where they were taken. The app places them with AI. You place the ones it can't, and later the app refines your placement.

| | |
| --- | --- |
| Target users | Anyone who wants to keep the memories of a place: a first apartment, a dorm room, a family home, a childhood bedroom |
| Scale | One room for now. Later, a place should grow by adding more recordings (a hallway, the next room) |
| Platform | A web page that works on a phone first. A native mobile app later |
| Viewing | Inside the app. Sharing with other people is wanted; how it works is still open (see "Open questions") |

### How this changed from P2-A2

The P2-A2 submission was **Clearance**: scan a room and check whether furniture from an online store fits before you buy it. It targeted students and renters furnishing a place (`docs/Clearance_Project_Idea_Description (older idea).pdf`). Memory Room keeps the same technical core: an ordinary phone video becomes a metric 3D room through MapAnything. It changes the problem from "will this item fit?" to "keep this place and the photos taken in it". The browser extension, the fit editor and the clearance checks are dropped.

## Core features

| # | Feature | What the user does | Status |
| --- | --- | --- | --- |
| 1 | **Capture** | Films the room; gets back a 3D room to turn and zoom | Upload works. The 3D build runs in a Colab notebook that has not yet run on a real video; `import_room` brings its result in, and the 3D room page shows it |
| 2 | **Memory map** | Adds photos; sees each one as a dot where it was taken; places the ones the AI could not | Photo upload works (many at once, private). The 3D page draws pins as dots and shows a tapped dot's photo. Placement is coded but never run; pins are not yet made by the app |
| 3 | **Versions over time** | Films the place again later; switches between versions; sees each photo in the version it belongs to | Chosen 17 Nov. The data model allows several scans per place; lining two scans up (AI feature 5) is not started |

The third feature was chosen from these on 17 Nov (A):

| Option | What it is | For | Against |
| --- | --- | --- | --- |
| A. Versions over time | Film the place again later; switch between versions; each photo shows in its own version | The builder's own idea. The data model already allows it. It gives people a reason to come back. Lining up two scans would also let a place grow with more recordings | Lining up two scans of the same room is untested. The fallback is showing them side by side |
| B. Sharing | Send a link; others view the room; later they add their own photos | Brings in new people | Needs share links, access rules and privacy work |
| C. Search and timeline | Find photos by caption or date; browse them in time order | Easiest. It also meets the class's "data feature" requirement | Every photo app already has it |

## Built

| Piece | What works | Where | How it was checked |
| --- | --- | --- | --- |
| Accounts | Sign up, log in, log out | `accounts/` | Tests |
| Places | Create, open, rename and delete a place; each user sees only their own | `rooms/` | Tests; a check against a running server |
| Room video upload | Add an MP4 or MOV video (up to 500 MB) to a place; list and delete videos | `rooms/` | Tests; a check against a running server with a stand-in video |
| Photos | Add up to 50 photos to a place at once (JPEG, PNG, WebP, 20 MB each); the date is read from inside each photo; caption, re-date and delete; only the owner can fetch a photo file | `rooms/` | Tests; a check against a running server with small made-up photos |
| Room import | `manage.py import_room <scan> <room folder or zip>`: checks a room built in Colab, attaches its points (PLY) to the scan, keeps its facts, marks it ready. Made-up rooms only with `--made-up`, and labelled | `rooms/management/commands/import_room.py`, `rooms/roomfolder.py` | 21 tests; run on the made-up demo room. **Not yet run on a real room** |
| 3D room page | `/scans/<n>/room/`: the room as coloured dots in three.js, photos as dots (tap one to see it), two views, a MADE-UP ROOM notice when it applies; linked from the place page; owner only | `rooms/views.py`, `rooms/templates/rooms/scan_room.html`, `static/viewer/` | 12 tests; seen in Chromium with the made-up demo room, at desktop and phone width. **Not yet shown a real room or opened on a phone** |
| Data model | Place, Scan, Memory and Pin tables with their rules | `rooms/models.py` | Tests |
| Build-room notebook | Video → 60 sharp frames → MapAnything → levelled, coloured 3D points, with each frame's camera. The floor is the lowest flat layer, and the room is levelled by the floor's own plane | `ai/build_room_colab.ipynb`, `ai/roompipe`, `ai/roomgeom` | 109 tests and full rehearsals with a stand-in model. **First real run 18 Nov** on a Colab T4 (`room-20261118-1342`): 60 frames, 393,033 points. It took the bed top for the floor; fixed the same day, and that room re-levelled on the laptop |
| Re-level a room | `python -m roompipe relevel --room <old room or zip> --out <new folder>`: corrects a room built before the floor fix, with no GPU | `ai/roompipe/relevel.py`, `roomgeom.level.relevel` | 7 tests; run on the first real room (the floor was 1.9° off level and 0.66 m below the false floor) |

Django tests passing on 18 Nov 2026: 240 of 240.

## AI features

| # | AI feature | In → out | Model or method | Status |
| --- | --- | --- | --- | --- |
| 1 | **Build the room** | About 60 frames from the room video → a 3D point for every pixel, with its colour, and the camera position of every frame | MapAnything, Apache-licensed weights, on a GPU. Picking frames (OpenCV) and levelling the room are ordinary code, not AI | Coded; never run on real data |
| 2 | **Place a photo** | A photo plus the room's frames → where the camera stood, or "can't place" | As designed: MapAnything run with about 20 room frames, then lined up with the stored room; run twice and trusted only if both runs agree. An alternative to test: match the photo's details against the room's frames and solve for the camera (ALIKED, LightGlue and OpenCV) | Designed method coded, never run. Alternative not built |
| 3 | **Refine a hand-placed photo** | A photo plus the spot the user tapped → the exact spot | Search only the frames near the tapped spot, then match and solve as in 2. If nothing matches (a selfie against a bare wall), keep the user's spot | Idea, 17 Nov. **Important; to discuss** |
| 4 | **Find a room's photos** | A large batch of photos → the ones taken in this room | Photo date (when the person lived there), GPS (the right building) and visual likeness to the room's frames (an image model such as DINOv2) | Planned for after 18 Nov |
| 5 | **Line up two scans** | A new scan plus an older one → both in the same coordinates | MapAnything or matching, as in 2, on frames from both scans | Needed for core feature 3 (versions) and for growing a place; not started |

Running the AI costs GPU time only. The models are free and open; there is no paid AI service. The Colab notebook runs on a free Colab GPU. A rented L4 GPU costs about $0.80 an hour (Modal's price page, checked 17 Nov 2026). How long one room takes is unknown until the first real run.

## Planned for the final submission (8 Dec)

The class requires these whatever the product. Points are out of 100 for the final.

| Item | Class part (points) | Notes |
| --- | --- | --- |
| The AI runs from inside Django, not a notebook | AI (25) | A Django view starts a GPU job and shows the result |
| A 3D viewer page with the real room and photos as dots | Scope (10), AI (25) | Photos it couldn't place are highlighted for the user to place |
| A JSON API | Django (25) | For example: get a room with its pins; move a pin |
| A data feature | Django (25) | Search and a timeline of a place's photos (17 Nov); an export of your own photos and captions is a candidate too |
| Model-choice write-up and AI error handling | AI (25) | Bad video, unreadable photos, GPU failures, uncertain answers |
| Evaluation | Testing (15) | Metrics; five realistic tests in a table (input, expected, actual, quality 1–10, time taken); two real failures; one improvement with before and after |
| Deployment | Deployment (15) | A live host; the resources needed; two deployment options compared on cost; what changes at 10,000 daily users; security and reliability |
| README, AI documentation, clean code | Docs (10) | `README.md` and `README_AI.md` |
| A three-minute video | Required | Overview, main workflow, the AI working in Django, limits and next steps |
| Versions over time (core feature 3) | Scope (10), AI (25) | Needs AI feature 5; the fallback is showing versions side by side |

## Set aside for later

| Idea | Why later | Notes |
| --- | --- | --- |
| **Find photos in the gallery** | Builder, 17 Nov: after 18 Nov | A web page only receives the files a person picks, so a web version would be "pick a batch, the AI keeps this room's photos" (AI feature 4). Scanning the whole gallery needs a native app. Google Photos reportedly limited outside apps to photos the user picks in 2025; check before relying on it |
| **Refine hand-placed photos** | Builder, 17 Nov: important, discuss later | AI feature 3. Fine for the first draft, where the builder is the only user and picks the photos |
| **Sharing** | Builder, 17 Nov: design later | Sharing is wanted. See "Open questions" |
| **Grow a place with more recordings** | Builder, 17 Nov: one room for now | Needs AI feature 5. Open question: how a scan that adds a new part of a place differs from a scan that is a later version |
| **Show how to film, before filming** | Builder, 17 Nov: later | An example video or short guide in the app. The written version exists: `docs/filming-guide.md` |
| **How photos look in the room** | Builder, 17 Nov: dots for now | Later options: a small camera cone pointing where the photo looked, which flies you to that view when tapped ("then and now"); floating thumbnails. Cones need the camera's direction, which a Pin does not store yet |
| **A more photo-like room** | After the first real run | Dots first. Then a mesh built from the model's depth, or a Gaussian splat (MapAnything documents an export for it) |
| **Native mobile app** | After the class | Brings gallery access, the phone's own position tracking while filming (ARCore), and uploads that continue in the background |
| **Privacy work** | Fine while the builder is the only user | Remove GPS from stored photos; consent for photos of friends; deletion. Must come before sharing |
| **Smaller items** | Later | iPhone HEIC photos; password reset; a limit on login attempts; voice notes; captions are already in the model |

## Product decisions

Technical decisions and their reasons are in `docs/system-map.md`. These are the product-level ones.

| Date | Decision | By |
| --- | --- | --- |
| 16 Nov 2026 | Memory Room replaces Clearance as the Project 2 idea | Builder |
| 16 Nov 2026 | A web page first; native app later | Builder (research design) |
| 16 Nov 2026 | A pin is its own record (photo, scan, x, y, z), so a photo can have a position in every scan of its place | Builder |
| 16 Nov 2026 | For the first draft, the AI runs in Colab as an experiment; Django starts it by the final | Builder |
| 17 Nov 2026 | Target users: anyone who wants to keep the memories of a place, not only students moving out | Builder |
| 17 Nov 2026 | Photos show as dots for now | Builder |
| 17 Nov 2026 | Photos the AI can't place are highlighted; the user places them; the app then refines the spot | Builder (refinement: to discuss) |
| 17 Nov 2026 | Scale: one room now; growing a place with more recordings later | Builder |
| 17 Nov 2026 | Gallery search after 18 Nov | Builder |
| 17 Nov 2026 | Sharing wanted; design later | Builder |
| 17 Nov 2026 | Third core feature: versions over time. Search and a timeline become the class's data feature instead | Builder (recommended) |
| 17 Nov 2026 | D2: photos are added many at once, the web version of picking from the gallery | Builder (recommended) |
| 17 Nov 2026 | D3: a photo file is served only through the owner check, never at an open address | Builder (recommended) |
| 17 Nov 2026 | The viewer reads the room's points as PLY | Builder (recommended) |
| 17 Nov 2026 | A built room reaches the app through a command run on the downloaded room folder; it attaches the room to its scan and marks it ready | Builder (recommended) |
| 17 Nov 2026 | Film in portrait, so the photos to place (mostly portrait) are not cropped when run with the room's frames | Recommended in the notebook review; see `docs/filming-guide.md` |

## Open questions

- [ ] Sharing and export. The builder's first thought: rooms are viewed only in the app, but can be shared with other people. Should a share link open in any browser without an account? Should people be able to take their own photos and captions out of the app?
- [ ] How AI feature 3 (refining a hand-placed photo) behaves when it disagrees with the user.
- [ ] How a scan that extends a place differs, in the data, from a scan that is a later version.
- [ ] Whether the instructor accepts a rented GPU as part of the deployment.

## Ideas worth a look

From the system guide (16 Nov) and the critical review (17 Nov). None of these is decided.

- **Placement:** match the photo's details to the room's frames and solve for the camera, instead of running the model twice. The number of matching details then measures confidence.
- **AI suggests, the user confirms:** an AI-placed dot asks "Is this where you stood?". One tap accepts it; a drag corrects it. Every answer becomes test data for the evaluation.
- **Keep every placement attempt:** a record of what the AI said, apart from where the dot ends up. The evaluation needs both.
- **Store the camera's direction on a pin:** needed for cones and "then and now". Cheapest before any pin exists.
- **Test placement with ground truth:** lay numbered sheets of paper on the floor before filming, take photos standing on them, and compare against "the centre of the room" as a baseline.
- **The look:** hide the ceiling for the dollhouse view; show the real video frames at their positions.
- **GPU jobs:** Modal's `spawn` and poll, so the GPU never has to call Django back.
- **Uploads:** send videos straight to file storage (Cloudflare R2) with a progress bar; later, pick frames in the browser so the video never leaves the phone.
- **Phone tracking in the browser:** Chrome on Android can expose the phone's position through WebXR. iPhone Safari cannot.
- **Another model if the room disappoints:** Depth Anything 3 (Base, Small and Metric-Large are Apache-licensed).

## Where the ideas came from

- `docs/Clearance_Project_Idea_Description (older idea).pdf`: the P2-A2 submission.
- `docs/reference/05-I-M2-memory-room.md`: the full Memory Room idea, with competitors and risks.
- `docs/reference/06-I-M2-technical-feasibility-check.md`: a skeptical check of the technical design.
- `docs/design/2026-11-16-first-draft.md`: what the first draft builds and why.
