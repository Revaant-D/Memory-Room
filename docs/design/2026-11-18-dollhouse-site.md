# The Dollhouse look: design

**Date:** 18 Nov 2026. **Status:** waiting for the builder's approval.
**Mockup it comes from:** `docs/design/mockups/a-dollhouse.html` (direction A, chosen by the builder on 18 Nov over B "Plan" and C "Window"). **Mockup of this design:** `docs/design/mockups/a2-dollhouse-app.html`, every page below, clickable (the builder asked to see it before approving).

## Why

The builder wants a site that does not look generated or generic, with no feature or sentence that isn't needed, where every move through the site has a purpose. It also has to look good in a recorded demo. Direction A treats the app as one space: your room sits on a slate field like a model on a table, and moving through the app is the camera moving through that room.

## Goals

- The real room is the centre of the site: the landing page, your places and each place show it.
- Photos live inside the room as pink dots. Opening one flies the camera to where it was taken.
- Photos with no position are easy to spot, and you place them by tapping where you stood (decided 17 Nov).
- The same look runs through every page, the forms included.
- It works on a phone first (the platform decision of 16 Nov).

## Not in this piece

- AI placement from inside Django (on the 8 Dec plan). No pin made tonight comes from the AI.
- Versions over time, sharing, search and the timeline.
- Deleting or un-placing a pin. A placed photo can be moved, but not un-placed.

## What would make it a failure

- Text or controls that don't earn their place.
- A demo that shows something the app doesn't really do. Every dot on screen is a real pin.
- Breaking the privacy rule: a photo file is only ever served through the owner check (D3).

## Approaches considered (structure)

| | What | Chosen? |
| --- | --- | --- |
| Pages + transitions | Keep Django's pages and addresses. The place page becomes the 3D room; opening a photo moves the camera with no page load; page-to-page moves use the browser's view transitions | **Yes (builder, 18 Nov)**: low risk, keeps the 240 tests mostly valid |
| One-page app | One page, one scene, JSON endpoints, history handled in JavaScript | No: rewrites most views and tests the day the draft is due |

## What the builder decided (18 Nov)

1. **Direction A, Dollhouse.**
2. **Pages + transitions** (above).
3. **Landing room: the builder's own room, no photos.** A thinned copy of Octave Room's points is served openly for the landing page. Photos stay owner-only.
4. **Timing: build it now**, for the demo.
5. **Add a direction to Pin.** A nullable field saying which way the camera faced and how wide it saw. Placements that know it (the AI's, later) open with the photo lined up with the room; hand placements leave it empty and open as a card at the spot. This changes the §6 data model approved on 16 Nov.
6. **Place photos by hand tonight** (already a product decision of 17 Nov). No video frames are imported as photos.

## The design

### Look

| Token | Value | From |
| --- | --- | --- |
| Field | `#3e4752`, lit to `#4c5663` under the room | the bedspread's slate |
| Ink | `#eef0f2`, soft `#a9b2bc` | |
| Memory | `#ff6fae` | the room's pink light |
| Display type | Gloock (place names, page titles) | |
| Text type | Onest | |

Pill-shaped pink buttons for the one main action on a page; underlined text for the second. No cards, no capitals labels. Forms sit as a narrow column on the slate field, with the room faint and blurred behind them (the public landing room when logged out, the place's room inside a place).

### Pages

| Page | Address (unchanged) | What it becomes |
| --- | --- | --- |
| Landing | `/` (logged out) | The public room's dots gather into the room, turning slowly. "Keep the room." One line. Sign up, Log in. With no public room set up, the same page without the room |
| Sign up, Log in | as now | A narrow form on the slate field |
| Your places | `/places/` | Each place with a built room is drawn as a small model turning on the field, its name under it. Places without one, and "Film a new place", are empty dashed footprints in a column at the right (a row along the bottom on a phone) |
| A place | `/places/<slug>/` | **With a built room:** the room fills the screen, seen from above with the walls cut low; pink dots for placed photos; a strip of every photo along the bottom, unplaced ones dashed. Tap a dot or a photo: the camera flies to where it was taken. A top bar: back to places, the name, "Add photos", and a menu (add a room video, the videos, rename, delete). **Without one:** the name, what's missing ("Add a room video"), and the photos as a grid |
| A photo, opened | same page, `?photo=<id>` | **With a direction:** the camera stands where the photo was taken and the photo sits in the room, lined up, the room dimmed around it. **Without one (hand-placed):** the camera looks down at the spot from across the room, its dot highlighted, and the photo shows as a card beside it, "Placed by you". Both: caption, date, Edit, Move, previous and next; the back link reads "Room" |
| Placing | same page | Tap an unplaced photo (or Move): the camera goes overhead, "Tap where you stood", the tap saves the pin |
| 3D room of one scan | `/scans/<n>/room/` | The same room view, for that scan |
| Forms (add photos, add a video, rename, delete, edit a photo) | as now | Restyled; content unchanged |

### New server parts

- **`Pin.camera`** (JSON, nullable): `{"rotation": 3×3 camera-to-room rotation (OpenCV axes, as in cameras.json), "vfov": degrees}`. Checked in `Pin.clean()`: nine finite numbers, field of view between 1 and 179. One migration.
- **Save a pin by hand:** `POST /scans/<n>/pins/` with `memory`, `x`, `y`. Owner only; the photo must be of the same place; x and y finite and inside the room's box. Creates the pin, or moves the existing one (one pin per photo per scan). `placed_by = "user"`, `camera = null`. Answers with the pin as JSON.
- **Landing room:** `manage.py landing_room <scan>` writes a thinned copy of that scan's points (at most 150,000) to `media/landing/room.ply`; `/landing/room.ply` serves it to anyone. No photos, captions or names go with it. `manage.py landing_room --remove` takes it down.

## Calls made by Claude (overrule any)

1. The place page shows the room when a ready scan exists (`newest_ready_scan`); the old separate list of scans moves into the place's menu.
2. A hand-placed pin is stored 1.4 m above the floor (the first room's cameras sat at 1.15 to 1.4 m).
3. The room is turned in the browser so its walls line up with the screen (the scan is not wall-aligned). Pins and directions are turned with it; nothing stored changes.
4. `static/viewer/roomviewer.js` is replaced by a new viewer module written from the mockup's engine; `loaders.js` (the checked PLY reader) is kept.
5. The places page draws a live room for at most three places; more are listed by name.
6. Opening a photo adds `?photo=<id>` to the address (no reload), so a link opens straight to it.
7. People with reduced motion set get cuts instead of flights.
8. The "early version" note on the home page goes; `FIRST_DRAFT.md` already says what works.
9. Moving between pages uses cross-document view transitions; Firefox, which lacks them, just loads the page.

## Bug review before the build (18 Nov)

The builder asked for a thorough look for bugs before building. Each item was confirmed by reading the code or by trying it in the browser (marked), and each becomes a rule for the build and, where it can be, a test.

### In the server design (these would have shipped)

| # | Bug | How found | How the build avoids it |
| --- | --- | --- | --- |
| S1 | The browser turns the room so its walls line up with the screen. A tap on the floor is in the turned frame; saved as it is, every hand-placed pin lands in the wrong spot | Reading the design | The page turns the tap back into the scan's own frame before sending it. A Django test can't see this, so a browser check places a pin, reloads, and confirms the dot comes back under the same spot |
| S2 | `import_room` on a scan that already has pins replaces its points without a word. A re-built room (such as a re-levelled one) has a different frame, so every pin then points at the wrong place | Code: `import_room.py`, lines 60–75 | The command refuses when the scan has pins, and says how many. `--drop-pins` deletes them on purpose. Tested both ways |
| S3 | Deleting a room video says "Your photos stay", but every placement in that scan is deleted with it (Pin → Scan is CASCADE) | Code: `scan_confirm_delete.html` | The page says how many photos lose their place in the room when there are any. Tested |
| S4 | The design dropped the MADE-UP ROOM notice, which every page showing a stand-in room must carry (`models.py`, `Scan.room_info`) | Reading the design against the code | The room page keeps the notice; `landing_room` refuses a made-up room. Tested |
| S5 | A tap inside the room's box but outside the floor (the empty corner of an L-shaped room, like Octave Room) would be accepted | Reading the design; the plan shows the L | The page only accepts a tap where the scan has floor points (a 10 cm grid made when the room loads). The server keeps the box check as the backstop |
| S6 | Moving a photo the AI placed would keep its direction, so it would open lined up from the wrong spot | Reading the design | Moving a pin clears `camera` and sets `placed_by` to `user`. Tested |
| S7 | The design named neither which id `?photo=` carries nor how Back behaves. Replacing the address would make a phone's Back button leave the room instead of closing the photo | Reading the design | `?photo=<memory id>`, added with pushState; Back closes the photo. An unknown or other person's id is ignored, and the room opens normally. Tested (server side) |
| S8 | A place's scan can be uploaded, building, failed, or ready. The design covered only "no room" and "ready" | Reading the design against `Scan.Status` | The no-room page has a line for each state |

### In the mockup's code (the build is new code; each is a rule for it)

| # | Bug | Confirmed in the browser | Rule for the build |
| --- | --- | --- | --- |
| M1 | A flight cut short by another one turns the drag controls back on mid-flight, so the camera fights the new move | Yes: controls on 150 ms into the second flight | Each flight carries a number; only the latest one may finish or turn the controls on |
| M2 | Hiding a dot or button with `hidden` does nothing, because the CSS gives it a display | Yes: dot `grid`, button `flex` while hidden | `[hidden] { display: none !important; }` in the stylesheet |
| M3 | The place's name under the turning model wanders (112 px in 2.5 s) | Yes | The name sits at a fixed spot under the model, not on a turning point |
| M4 | With a photo open, its "Room" back link does nothing (it points at the address already showing) | Yes | Back from a photo is history: it closes the photo (with S7) |
| M5 | With many photos, the first ones in the strip are pushed off the left edge and can't be scrolled to | Yes: 50 photos, first at −967 px | The strip starts at the left when it overflows (`justify-content: safe center`) |
| M6 | Controls that are faded out can still be reached with the Tab key (50 of them) | Yes | Anything not showing is `inert` |
| M7 | Tapping on an existing dot while placing a photo silently cancels the placing | Yes | Dots don't take taps while placing |
| M8 | A delayed step (a timer, or the end of a flight) runs even after you've moved on: leaving the landing within 1.8 s put the landing text over the login page and hid the form | Yes | Every delayed step checks it still belongs to what's on screen (as M1) |
| M9 | The model keeps turning for people who have reduced motion set | Code | No turning, no gathering dots, cuts instead of flights |
| M10 | The room is redrawn 60 times a second even when nothing moves (the current viewer deliberately draws only on change, "a still room uses no battery"). Behind a blurred form page this would be a full-screen blur every frame | Code | Draw only while something moves. The form pages draw one still frame of the room and stop |
| M11 | Captions and place names are put into the page as HTML, so a caption could carry code | Code | User text is set as text, never as HTML (as the current viewer does) |
| M12 | Camera positions are worked out once, at load; turning a phone sideways leaves them wrong | Code | They are worked out again on resize |

Checked and not a bug: the ceiling coming back while the camera dives into the room does not block the view.

## Left to the build

Exact camera positions, timings and copy, judged in the browser at desktop and phone width.

## Checks

Django tests for: the new field's rules, the pin endpoint (owner, place, numbers, box, upsert, GET refused, moving clears the direction), the landing command and file (refuses a made-up room), the place page in each scan state, `?photo=` with a good, unknown and foreign id, the landing page with and without a room, `import_room` with pins (refused, and `--drop-pins`), and the delete-video wording. Every existing test kept passing or changed on purpose, with the reason recorded. Then a browser check of every page at 1280 px and 390 px.
