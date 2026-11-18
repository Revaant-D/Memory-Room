# The Dollhouse look: build plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Memory Room the approved Dollhouse look: the room is the centre of every page, photos are pink dots in it, and you can place a photo by tapping where you stood.

**Architecture:** Django keeps its pages and addresses. The place page becomes the full-screen 3D room when the place has a ready scan; opening a photo, placing one and moving between photos happen in that page without reloads. A new viewer module (`static/viewer/room3d.js`) replaces `roomviewer.js`; its pure geometry lives in `static/viewer/roomgeom.js` so Node can test it. Three new server parts: `Pin.camera`, `POST /scans/<n>/pins/`, and the public landing room.

**Tech stack:** Django 5 (project `.venv`), three.js r170 (vendored), Node 24's built-in test runner for the geometry module, Gloock and Onest from Google Fonts.

**Spec:** `docs/design/2026-11-18-dollhouse-site.md` (approved 18 Nov, with its bug review S1–S8, M1–M12). Mockup: `docs/design/mockups/a2-dollhouse-app.html`.

## Global constraints

- Tokens, exactly: field `#3e4752`, lit `#4c5663`, ink `#eef0f2`, ink-soft `#a9b2bc`, memory `#ff6fae`, danger `#ff9b8a`. Display type Gloock; text Onest.
- Photo files only ever through `memory_photo` (D3). The landing room carries no photos, captions or names.
- User text (captions, place names) reaches the page as text: Django escaping in templates, `json_script` for data, `textContent` in JavaScript. Never `innerHTML` with user text (M11).
- Every page that shows a made-up room says MADE-UP ROOM (S4).
- Hand-placed pins: `z = 1.4`, `placed_by = "user"`, `camera = None` (design call 2; S6).
- Commit and push only when the builder asks (CLAUDE.md). No commit steps below; the builder decides.
- Tests: `.venv\Scripts\python.exe manage.py test` (Django), `node --test "static/viewer/tests/*.test.mjs"` (geometry).

## Review focus

1. A tap is saved in the turned frame (S1): `toScan` must undo `turn` exactly; Node test round-trips points at several angles, and the browser check reloads after placing.
2. A pin POST for another user's photo, another place's photo, or a scan that isn't ready: must answer 404/400 and save nothing (Task 2 tests).
3. Two flights or delayed steps overlapping (M1, M8): a fast double tap on two photos must end on the second photo with drag controls off (browser check, Task 11).
4. A place with 0 photos, or 50 (M5): the strip must be empty-but-usable and fully scrollable (browser check, Task 11).
5. A phone turned sideways mid-view (M12): views recomputed (browser check, Task 12).

---

### Task 1: `Pin.camera`

**Files:** Modify `rooms/models.py` (Pin); create `rooms/migrations/0005_pin_camera.py` (makemigrations); test `rooms/tests/test_models.py`.

**Produces:** `Pin.camera`: `JSONField(null=True, blank=True)`, shape `{"rotation": [[r00,r01,r02],[r10,r11,r12],[r20,r21,r22]], "vfov": float}`. Rotation is camera-to-room (scan frame), OpenCV camera axes, as in `cameras.json`.

- [ ] Tests (in a new `PinCameraTests` class): `test_camera_is_optional` (pin saves with `camera=None`); `test_camera_accepts_rotation_and_fov` (identity rotation, vfov 60 saves); `test_camera_rejects_bad_shapes` (each of: not a dict, missing `rotation`, 2×3 rotation, a `"x"` entry, `float("nan")` entry, vfov `0`, vfov `180`, vfov `"wide"`) raises `ValidationError` on save.
- [ ] Run, see them fail.
- [ ] Add the field and a check in `Pin.clean()`: rotation is 3 lists of 3 finite numbers; vfov a finite number with 1 < vfov < 179; error text "A pin's camera must be a 3×3 rotation and a field of view between 1 and 179 degrees." Run `makemigrations rooms -n pin_camera`, `migrate`.
- [ ] Run all tests; all pass.

### Task 2: Save a pin by hand

**Files:** Create `rooms/pins.py` (the view), modify `rooms/urls.py`; test `rooms/tests/test_pin_save.py`.

**Consumes:** `get_own_scan`, `get_own_memory` (`rooms/access.py`); `Pin` (Task 1).
**Produces:** URL name `pin_save`, `POST /scans/<int:pk>/pins/`, form fields `memory`, `x`, `y`. Success: `200`, JSON `{"pin": {"memory": id, "x": x, "y": y, "z": 1.4, "placedBy": "user", "camera": null}}`. Errors: JSON `{"error": text}` with `400`. Function `pin_json(pin) -> dict` (same shape) is reused by Task 3.

- [ ] Tests: `test_needs_login` (302 to login); `test_get_refused` (405); `test_places_a_photo` (creates the pin, values above); `test_moves_an_existing_pin_and_clears_its_camera` (pin with `placed_by="ai"` and a camera → after POST: new x, y, `placed_by="user"`, `camera=None`, still one pin); `test_other_users_scan_404`, `test_other_users_photo_404`; `test_photo_of_another_place_400`; `test_scan_not_ready_404`; `test_not_numbers_400` (`"abc"`, `"nan"`, `"inf"`); `test_outside_the_box_400` (x below `box.low[0]`, y above `box.high[1]`); `test_csrf_enforced` (`Client(enforce_csrf_checks=True)` without token → 403).
- [ ] Run, see them fail.
- [ ] Implement `pin_save(request, pk)` with `@login_required` and `@require_POST`: scan via `_get_own_built_scan` (move it from `views.py` into `access.py` as `get_own_built_scan` so both modules share it); memory via `get_own_memory`; floats via `float()` + `math.isfinite`; box from `scan.room_info["box"]`; `update_or_create` on `(memory, scan)`.
- [ ] Run all tests; all pass.

### Task 3: The room page on the server

**Files:** Create `rooms/room_page.py`; modify `rooms/views.py` (`place_detail`, `scan_room`, `scan_delete`), `rooms/templates/rooms/room.html` (new, minimal shell now; Task 11 fills it), delete `rooms/templates/rooms/scan_room.html`; tests: `rooms/tests/test_scan_room.py`, `rooms/tests/test_places.py`, `rooms/tests/test_scans.py`, `rooms/tests/test_memory_pages.py`.

**Produces:** `room_context(scan, open_id=None) -> dict` with keys `scan`, `place`, `made_up`, `room_data`. `room_data` (to `json_script` id `room-data`):
`{"points": url?v=, "box": box, "madeUp": bool, "pinUrl": url, "photos": [{"id", "caption", "date" ("18 Nov 2026" or ""), "src", "edit", "pin": pin_json|null}], "open": memory id or null}`. Photos in `Memory` order. `open` is the `?photo=` id only if it is one of this place's photos (S7).

- [ ] Tests (rewrite `test_page_shows_the_viewer` to expect `viewer/room3d.js` and the new data; keep the made-up, caption-escape, other-scan tests on the new shape): `test_place_page_is_the_room_when_ready` (place page contains `id="room"` and room-data for `newest_ready_scan`); `test_place_page_without_a_room` (no ready scan: "Add a room video" link, no `id="room"`); one test per scan state for the line shown (S8): uploaded "Its room isn't built yet.", building "The room is being built.", failed "The room couldn't be built from this video."; `test_unplaced_photo_has_no_pin`; `test_open_photo_from_address` (`?photo=<id>` → `open` = id); `test_open_ignores_unknown_and_foreign_ids`; `test_delete_video_counts_lost_placements` (S3: with 2 pins the page says "2 photos lose their place in the room"; with none it says "Your photos stay."). Update the older place-page tests that expect the old layout ("Room scans", "View the room in 3D", "· Uploaded", "(no caption)") to the new copy, each change on purpose.
- [ ] Run, see the new ones fail.
- [ ] Implement `room_context`; `place_detail` renders `rooms/room.html` when `place.newest_ready_scan()` exists, else `rooms/place_detail.html` (setup: name, the state line of the newest scan, "Add a room video", photo grid); `scan_room` renders `rooms/room.html` for that scan; `scan_delete` passes `lost = scan.pins.count()`.
- [ ] Run all tests; all pass.

### Task 4: `import_room` keeps pins safe (S2)

**Files:** Modify `rooms/management/commands/import_room.py`; test `rooms/tests/test_import_room.py`.

- [ ] Tests: `test_refuses_when_the_scan_has_pins` (CommandError naming the count, e.g. "Scan 1 has 2 placed photos"; points file and pins unchanged); `test_drop_pins_replaces_and_deletes_them` (`--drop-pins`: imports, pins gone, says how many were removed).
- [ ] Run, fail; implement the check before anything is written; run all tests; pass.

### Task 5: The landing room

**Files:** Create `rooms/landing.py` (`LANDING_FILE = "landing/room.ply"`, `landing_exists() -> bool`, `write_landing(scan, max_points=150_000) -> int`), `rooms/management/commands/landing_room.py`, view `landing_points` in `rooms/views.py`, URL `landing/room.ply` name `landing_points`; `home` passes `landing` (URL or None); test `rooms/tests/test_landing.py`.

**Produces:** `landing_points` (public, `Cache-Control: public, max-age=3600`, 404 when absent).

- [ ] Tests: `test_command_writes_a_thinned_copy` (a 10-point PLY with `max_points=4` → a valid PLY of ≤4 points, every point one of the originals); `test_command_refuses_made_up_room`; `test_command_refuses_scan_not_ready`; `test_remove_takes_it_down`; `test_file_is_public` (logged out → 200, bytes match); `test_404_when_absent`; `test_home_mentions_the_room_only_when_it_exists`.
- [ ] Run, fail; implement (every n-th point, n = ceil(count / max_points), written with the same 15-byte layout); run all; pass.
- [ ] Run it for real: `landing_room 1`.

### Task 6: Geometry module, tested in Node

**Files:** Create `static/viewer/roomgeom.js`, `static/viewer/tests/roomgeom.test.mjs`.

**Produces (pure functions, no three.js):**
- `wallAngle(positions: Float32Array, step = 7) -> radians` in [0, π/2): the turn about z that makes the walls (points 0.3–2.3 m up) pile into the sharpest x and y histograms (2 cm bins; 0.5° search).
- `turnXY(x, y, a) -> [x', y']` and `unturnXY(x', y', a) -> [x, y]` (exact inverse).
- `floorGrid(positions, cell = 0.1) -> {has(x, y): bool}` built from points with z < 0.1 (S5), in the frame of the given positions.

- [ ] Tests: `wallAngle` finds 20° (±0.5°) on synthetic walls of a box turned 20°; `unturnXY(turnXY(p))` equals p within 1e-9 for angles 0, 0.3, 1.2; `floorGrid` says yes inside a synthetic L-shaped floor and no in the L's empty corner.
- [ ] Run `node --test static/viewer/tests/`, fail; implement; pass.

### Task 7: Viewer engine `room3d.js`

**Files:** Create `static/viewer/room3d.js` (from the mockup's `shared/room.js`); delete `static/viewer/roomviewer.js`.

**Consumes:** `loadPoints` (`loaders.js`), Task 6.
**Produces:** `createRoom(container, {positions, colors, box, still = false}) -> room` with: `turn` (radians), `toScan(x, y)`, `fromScan(x, y)`, `onFloor(x, y)` (scan frame); `view(position, target, fov)`; `photoView(pin, widen)` (needs `pin.camera`); `spotView(pin)` (look down from across the room); `flyTo(view, ms, {orbit})` → Promise resolving `true` if it finished, `false` if a newer flight replaced it (M1); `animate(name, uniform, to, ms)`; `uniforms` (`cut`, `tint`, `near`, `spread`, `opacity`); `showPhoto(pin, src, on)`; `project([x,y,z] scan frame) -> {x, y, visible}`; `floorAt(clientX, clientY) -> [x, y] scan frame | null`; `onFrame(fn)`; `spin(speed)` (no-op under reduced motion, M9); `fitViews(fn)` called on resize (M12). Draws only while something moves (M10); `still: true` draws one frame and stops.

- [ ] Browser check on the room page once Task 11 exists (no unit test: WebGL).

### Task 8: The look across the site

**Files:** Rewrite `static/css/site.css`, `templates/base.html`, `templates/404.html`, `templates/500.html`, `templates/includes/form_fields.html` (if needed), `accounts/templates/registration/login.html`, `signup.html`, every form/confirm template in `rooms/templates/rooms/`; create `rooms/templatetags/backdrop.py` (`{% backdrop place %}` → points URL of the place's newest ready scan, or the landing URL when logged out and it exists, else nothing) and `static/site/backdrop.js` (one still frame, blurred, M10).

- [ ] Rules in CSS: `[hidden] { display: none !important; }` (M2); messages as a pill at the bottom that fades after 4 s; forms a 26 rem column; `@view-transition { navigation: auto; }`.
- [ ] Run all Django tests; fix only copy-level expectations, each on purpose.

### Task 9: Landing page

**Files:** `rooms/templates/rooms/home.html`, `static/site/landing.js`.

- [ ] Dots gather (3.2 s, none under reduced motion), slow spin, the text after 1.8 s only if still on the page (M8). Without a landing room: the text on the field, no canvas. Browser check.

### Task 10: Your places

**Files:** `rooms/templates/rooms/place_list.html`, `static/site/places.js`; `place_list` view passes, per place, its ready scan's points URL (first three with a room).

- [ ] Each ready place a turning model with its name fixed under it (M3), the whole model a link; other places and "Film a new place" as dashed plots (column at the right; row at the bottom under 600 px). Log out as a POST form. Empty state: one plot, "Film your first place". Browser check.

### Task 11: The room page

**Files:** `rooms/templates/rooms/room.html`, `static/site/room.js`.

- [ ] Top bar (back, name, MADE-UP ROOM line when it applies, ⋯ menu with Add photos, Add a room video, each video with its state and Delete, Rename, Delete this place); strip (placed, then unplaced dashed, then +), `justify-content: safe center` (M5); dots as buttons, off while placing (M7); everything not showing `inert` (M6).
- [ ] Open a photo: pushState `?photo=id`, popstate closes it (M4, S7); with `camera`: lined-up photo; without: `spotView` + card "Placed by you". Prev/next, arrow keys, Escape.
- [ ] Place/Move: overhead, "Tap where you stood", Cancel; tap → `floorAt` → `onFloor` else "That's outside the room" (S5) → POST in scan frame (S1) with `X-CSRFToken` → dot drops in; on error the text from the server.
- [ ] Browser checks: place a photo, reload, dot in the same spot (S1); double-tap two photos fast (M1); 50-photo strip (M5); Tab order (M6); keyboard Escape.

### Task 12: Finish

- [ ] Places → place continuity (sessionStorage flag: the room page starts from the places pose and dives).
- [ ] Full browser pass at 1280×800 and 390×844, every page, both logged in and out; rotate (M12); reduced motion (M9).
- [ ] All Django tests, Node tests. Record: `docs/system-map.md` (new piece, decisions), `docs/features.md`, run sheet, `CLAUDE.md`. Report results to the builder; commit only on their word.
