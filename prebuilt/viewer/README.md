# Component: viewer

**Is:** the 3D room in the browser. Coloured points you can turn, a pin for each photo, tap a pin to choose it, tap the floor to place one by hand. One JavaScript module with no knowledge of Django, a reader for both candidate points-file formats, and a standalone demo page.
**Is not:** a Django page. No template, view or address for it exists yet.
**Result (16 Nov 2026):** checked in a real browser (Chromium, driven by a script) against a made-up room of 110,302 points. Not checked on a phone, and never shown a real room.

## Why it was safe to build early

The approved design says the first draft shows the room "as coloured points in a three.js viewer page inside the app" (`docs/design/2026-11-16-first-draft.md`, §7). That much is decided. What is **not** decided, and is therefore left open here:

| Open decision | How this folder stays out of its way |
| --- | --- |
| The format of the points file | `loaders.js` reads both candidates, `bin` and `ply`. Delete the one not chosen |
| How a points file reaches a scan (admin, or an upload page) | Not touched. The viewer is handed arrays; it does not care where they came from |
| Whether a sample points file is kept in the repository | `demo/` holds one of each format. Note that `.gitignore` already excludes `*.bin` |
| Where three.js comes from (a copy in the project, or a CDN) | A copy is in `vendor/` so the demo works offline. See "Calls made here" |

## What is in it

| File | What it is |
| --- | --- |
| `roomviewer.js` | `createRoomViewer(container, options)`: draws the room and returns an object to control it. About 280 lines, commented throughout |
| `loaders.js` | `loadPoints(url)`, `parseBin(buffer)`, `parsePly(buffer)`: turn a points file into the two arrays the viewer wants |
| `demo.html` | A standalone page that shows the made-up room in `demo/`, with buttons for the two views and for placing a pin |
| `demo/` | `room.json`, `points.ply`, `points.bin`, `placements.json`: a **made-up** room, written by `python -m roompipe demo` (`prebuilt/ai/pipeline`) |
| `vendor/` | three.js 0.170.0 (`three.module.min.js`) and its `OrbitControls` add-on, unmodified, with their MIT licence. Downloaded from unpkg.com on 16 Nov 2026 |

## Seeing it

A page opened straight from disk cannot load other files, so it needs a local server:

```powershell
cd prebuilt\viewer
..\..\.venv\Scripts\python.exe -m http.server 8765
```

Then open `http://127.0.0.1:8765/demo.html`. Add `?format=bin` to load `points.bin` in place of `points.ply`. Stop the server with Ctrl+C.

The page says at the top that the room is made up. Keep that notice on anything that shows this data: the first-draft rules forbid presenting made-up results as real.

## What the viewer does

```js
const viewer = createRoomViewer(document.querySelector("#room"), {
  positions,                 // Float32Array, x y z per point (metres; floor z = 0, z up)
  colors,                    // Uint8Array, r g b per point (0 to 255)
  box: { low: [x, y, z], high: [x, y, z] },
  pins: [{ id, x, y, z, label, placedBy }],   // placedBy: "ai" or "user"
  onPinSelect(pin) {},       // a pin was tapped, or null when the tap missed every pin
});
viewer.setPins(pins);               viewer.selectPin(id);
viewer.setView("inside");           viewer.setView("above");
viewer.startPlacing(({ x, y, z }) => { ... });   viewer.cancelPlacing();
viewer.dispose();
```

- **Turning:** drag to turn, pinch or scroll to move closer, two fingers to slide. This is three.js's standard `OrbitControls`.
- **Two views:** "inside" stands near the middle of the room at eye height. "above" looks down into the room with the ceiling and the top quarter of the walls cut away, so the floor and all the pins can be seen at once.
- **Pins:** a ball where the photo was taken and a thin line down to the floor, because in a cloud of dots it is hard to judge how far away a floating ball is. Orange for placed by the model, blue for placed by a person. The chosen pin is drawn larger.
- **Placing by hand:** after `startPlacing`, the next tap on the floor calls back with the spot. `x` and `y` are where the tap hit the floor, to the centimetre; `z` is set to 1.5 m, eye height.
- **Drawing only when something changes,** not sixty times a second, so a still room does not drain a phone's battery.

## What was checked, in a real browser

| Check | Result |
| --- | --- |
| The page loads and draws all points, from `points.ply` and from `points.bin` | 110,302 points both ways |
| Each of the five pins, tapped where it appears on screen, becomes the chosen one | 5 of 5 |
| A tap that misses every pin clears the choice | Yes |
| "Place a pin", then a tap on the floor, adds a pin inside the room | Yes: (2.00, 1.15, 1.50) in a 4 × 3 m room |
| A drag while placing turns the room and does **not** place a pin | Yes |
| At phone width (390 px) the page does not scroll sideways and the room fills the width | Yes |
| A damaged points file gives a plain message, not a blank page | "The room could not be shown: Not a PLY file." |
| `dispose()` removes the canvas | Yes |
| No errors in the browser's console during any of the above | Yes (apart from the deliberate damaged-file error) |

Two screenshots were looked at by eye: walls, floor, bed, door and poster read as surfaces from inside, and the cut-away view from above shows the whole room and its pins.

## Not checked

- **A real phone.** Touch turning and pinch were not exercised; only mouse clicks and drags were. How fast 100,000 points draw on the builder's phone is unknown.
- **A real room.** The made-up room has clean, evenly spread points. A real reconstruction is noisier and patchier, and the feasibility check expects it to look "fuzzy". The 3 cm dot size was chosen by eye on made-up data.
- Safari and Firefox.
- A room with several hundred thousand points.

## Calls made here that the builder can overrule

1. **three.js is copied into `vendor/`** (690 KB) and not loaded from a CDN, so the page works with no internet, which matters for a class demo. If it goes into the app, it would live under `static/`.
2. **Dots are 3 cm wide** for points thinned to 2 cm, so surfaces close up. `pointSize` is an option.
3. **A hand-placed pin gets eye height (1.5 m)**, because a tap on a screen only gives a spot on the floor. The technical design's sketch says "ray from the tap to z = 0" and does not say what height the pin gets.
4. **Two views** ("inside", "above"). The design does not mention views. Outside a room made of dots you cannot see in, hence the cut-away.
5. **Colours are drawn exactly as stored**, with three.js's colour conversion switched off for the whole page.
6. **`loaders.js` accepts only the PLY layout Memory Room writes**, not every PLY. A different layout is refused with a message.

## Putting it into the app (not done; needs the decisions above first)

Roughly, for whichever session builds the viewer page:

1. Copy `roomviewer.js`, `loaders.js` and `vendor/` into `static/`.
2. A view for `/places/<slug>/room/` that uses `get_own_place` and `place.newest_ready_scan()` (both already in the kits), and a template with the import map from `demo.html`, a `<div id="room">`, and the pins passed with Django's `json_script`.
3. An owner-checked address for the points file, like the photo view in chunk 5 (D3 a), since `media/` is not public.
4. Each pin's `id` is the `Pin`'s id; `onPinSelect` shows that memory's photo and caption.
5. `startPlacing`'s callback posts `{x, y, z}` to a view that saves `Pin(memory, scan, x, y, z, placed_by="user")`. `Pin.save()` already enforces the rules.

Each of those is a small decision or page of its own, with its own Decide step.
