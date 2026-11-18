<!-- DRAFT for docs/system-map.md. Written 16 Nov 2026 before the chunk was applied.
     Before pasting: check it against the applied code, fix the test count if it moved,
     update "What exists today", "Last updated", the layout block and the test total at
     the top of the system map, and delete this comment. -->

## Piece 3: Data model

### What it does

Holds everything the app remembers, in four tables. A **Place** is a room. A **Scan** is one filmed video of that room and, later, the 3D points built from it. A **Memory** is one photo taken there. A **Pin** says where one memory sits inside one scan.

```
User ──< Place ──< Scan ──< Pin >── Memory
                └──────────────────< Memory          "──<" reads "has many"
```

| Table | Fields |
| --- | --- |
| Place | owner, name, slug (unique per owner), created |
| Scan | place, video, taken_on, status (uploaded / building / ready / failed), points_file, created |
| Memory | place, photo, caption, taken_on, created |
| Pin | memory, scan, x, y, z (metres; floor is z = 0, z points up), placed_by (user / ai), created |

No page uses these tables yet. They can be seen and edited in `/admin/`.

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/models.py` | The four models, and the three functions that choose where an uploaded file is stored |
| `rooms/slugs.py` | `unique_slug`: makes the word in a place's address |
| `rooms/signals.py` | Removes a scan's or memory's files from disk after its row is deleted |
| `rooms/apps.py` | `ready()` connects `signals.py` when Django starts |
| `rooms/admin.py` | Puts the four models in the admin site |
| `rooms/migrations/0001_place.py`, `0002_scan_memory.py`, `0003_pin.py` | Create the tables |
| `rooms/tests/utils.py` | Test helpers: a user, a real tiny JPEG, a stand-in video, a temporary media folder |
| `rooms/tests/test_models.py` | 28 tests |

### How one request flows

No page yet, so this traces a save. Saving a pin, from any code:

1. `Pin.save()` calls `self.full_clean()` before anything is written.
2. The field checks run: `placed_by` must be `user` or `ai`; x, y and z must be numbers.
3. `Pin.clean()` runs: the memory's place and the scan's place must be the same, and x, y, z must be finite (not "not a number", not infinity).
4. The unique rule runs: this memory must not already have a pin in this scan.
5. If any check fails, `ValidationError` is raised and nothing is written. Otherwise the row is inserted.

Saving a place for the first time: `Place.save()` sees an empty slug and calls `unique_slug(owner, name)`, which turns the name into a word (`Dorm Room 214` → `dorm-room-214`), cuts it to 70 characters, and adds `-2`, `-3`, ... while the word is `new` or this owner already uses it.

Deleting a place: Django deletes its scans, memories and pins with it (`on_delete=CASCADE`), and after each scan or memory row goes, `rooms/signals.py` removes that row's files from `media/`.

### The rules, and where each is enforced

| Rule (§6 of the design) | Enforced by | Proved by |
| --- | --- | --- |
| A place's address word is unique for its owner | `UniqueConstraint` on `Place`; `unique_slug` | `test_same_name_same_owner_numbered`, `test_same_name_two_owners` |
| A place can never sit at `/places/new/` | `RESERVED` in `rooms/slugs.py` | `test_reserved_word` |
| A place's address survives a rename | `Place.save()` only sets an empty slug | `test_slug_kept_on_rename` |
| A photo has at most one pin per scan | `UniqueConstraint` on `Pin` | `test_second_pin_same_scan_refused`, `test_one_pin_per_scan_allowed` |
| A pin's photo and scan belong to the same place | `Pin.clean()` | `test_pin_across_places_refused` |
| A pin says who placed it | `choices` on `placed_by`, checked in `Pin.save()` | `test_placed_by_must_be_stated` |
| A pin's position is three real numbers | `Pin.clean()` | `test_coordinates_must_be_numbers` |
| Deleting a scan deletes its pins and keeps the photos | `on_delete=CASCADE` on `Pin.scan` | `test_delete_scan_removes_pins_keeps_memory` |
| The viewer shows the newest ready scan | `Place.newest_ready_scan()` | `test_newest_ready_scan` |
| The phone's file name never reaches the disk | the three `*_path` functions | `test_stored_name_is_generated`, `test_video_stored_name` |
| Deleted rows do not leave files behind | `rooms/signals.py` | the three `test_delete_*_removes_*` tests |

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Pin is its own model: (memory, scan, x, y, z) | **Builder, 16 Nov** | A position only means something inside the scan it was measured in. Keeping it on its own row lets one photo have a position in every scan of its place, and lets a scan be deleted without touching the photo |
| The field list and the rules above | **Builder, 16 Nov** (approved §6) | |
| The slug is made once and never changes | Claude, 16 Nov | Old links keep working after a rename |
| A taken or reserved slug gets a number | Claude, 16 Nov | Simple, and readable in the address bar |
| Files are stored under a generated name in `places/<place id>/...` | Claude, 16 Nov | A phone's file name can contain anything, and can repeat. Only a short, plain ending is kept |
| The pin rules run in `save()`, not only in forms | Claude, 16 Nov | Pins will be written by scripts and by the placement step, which never pass through a form |
| "Not a number" and infinity are refused | Claude, 16 Nov | A failed placement run can produce them, and a viewer cannot draw them |
| Three migrations, one per step | Claude, 16 Nov | Each can be read on its own |

### How to change it

- **Add a field:** add it in `rooms/models.py`, then `makemigrations` and `migrate`. Add it to the model's admin class if it should show in a list.
- **Add a scan status:** add a line to `Scan.Status`. It needs a migration because the choices are recorded there.
- **Reserve another address word** (if a page is ever added at `/places/<word>/`): add it to `RESERVED` in `rooms/slugs.py`.
- **Change where files are stored:** the three `*_path` functions. Existing rows keep their old paths.

### Known gaps

- A file is removed as soon as its row is deleted, even if the surrounding database transaction is later rolled back. Nothing deletes inside a transaction today.
- Empty folders are left under `media/places/` after their last file goes.
- A place whose name has no Latin letters or digits gets the address word `place`.
