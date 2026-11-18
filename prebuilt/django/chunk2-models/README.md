# Kit: chunk2-models

**Is:** all of plan chunk 2 (Tasks 3, 4 and 5 of `docs/plans/2026-11-16-django-foundation.md`): the four models, their rules, the admin, and their tests.
**Needs:** chunk 1 as committed in `4ed4bda`. Nothing else.
**Result when laid on the project (16 Nov 2026):** 78 tests, all pass (50 from chunk 1, 28 new). `makemigrations --check` reports no changes. The tests leave nothing in `media/`.

## Why it was safe to build early

The builder approved the field list and the rules on 16 Nov (§6 of the design) and chose the separate Pin model. The plan lists no builder decision for this chunk.

## What is in `files/`

| File | New or replaces | What it is |
| --- | --- | --- |
| `rooms/models.py` | replaces the empty file | `Place`, `Scan`, `Memory`, `Pin`, and the three functions that name uploaded files |
| `rooms/slugs.py` | new | `unique_slug(owner, name)`: the word in a place's address |
| `rooms/signals.py` | new | Removes a scan's or memory's files from disk when its row is deleted |
| `rooms/apps.py` | replaces | Adds `ready()`, which connects `signals.py` |
| `rooms/admin.py` | replaces the empty file | The four models in `/admin/` |
| `rooms/migrations/0001_place.py`, `0002_scan_memory.py`, `0003_pin.py` | new | Made by `makemigrations`, one per plan task, not written by hand |
| `rooms/tests/utils.py` | new | `make_user`, `TempMediaTestCase`, `jpeg_file`, `video_file` |
| `rooms/tests/test_models.py` | new | 28 tests: every test the plan lists for Tasks 3, 4, 5 |

## Calls made here that the plan did not spell out

Read these to the builder together with the plan's "Claude's calls" for chunk 2. Each can be overruled.

1. **Only a short, plain ending is kept from an uploaded file's name.** `.jpg` and `.mp4` survive (lower-cased). An ending longer than five characters, or with anything but letters and digits, is dropped. The plan said only "the lower-cased extension"; this closes the case of a hostile or absurd ending. (`_ending()` in `rooms/models.py`.)
2. **A name in a script `slugify` cannot turn into plain letters becomes `place`, `place-2`, ...** This is what the plan's test asks for emoji; it also applies to, say, a Japanese name. The place's *name* is shown correctly everywhere; only the address word is generic.
3. **The pin rule messages:** "A pin's photo and scan must belong to the same place." (the plan's wording) and "A pin's position must be three real numbers." (written here).
4. **What each row is called in the admin** (`__str__`): a scan is "Dorm Room, filmed 01 Nov 2026"; a memory is its caption, or "Photo 12" when it has none; a pin is "Pin for memory 3 in scan 1".
5. **`test_long_name` uses a 79-character name.** The plan says 80; 79 was chosen so the 70-character cut lands exactly on a hyphen, which is the case the test is there to catch. The test also checks that a second place with the same long name still fits the column.
6. **`jpeg_file(taken=...)` was checked by hand, not by a test:** the date written into the test photo was read back with Pillow and matched. Chunk 5 depends on that helper.

## Known limits (true of the plan's design, not bugs in the kit)

- A file is removed the moment its row is deleted. If that delete were inside a database transaction that later rolled back, the row would return and the file would not. No view in the plan deletes inside a transaction.
- Empty folders (`media/places/7/scans/`) are left behind after the last file goes.
- Two requests creating a place with the same name at the same instant could both pick the same slug; the database's unique rule would refuse the second with an error page. One person on one phone cannot do this.

## Applying it

Follow "How to use a kit" in `prebuilt/README.md` with the name `chunk2-models`. After `--write`:

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test          # expect 78
```

Then the plan's **Walk through (chunk 2)** with the builder, and the Record step using `system-map-section.md` from this folder.

## If it no longer fits

`kit.py status` says BLOCKED when `rooms/models.py`, `rooms/admin.py` or `rooms/apps.py` in the project is no longer the untouched chunk 1 file. Open both versions; the project's files were empty stubs at `4ed4bda`, so whatever was added since is small and can be carried into the kit's version by hand.

If the builder changes a field or a rule: edit `files/rooms/models.py` and the matching test, delete the three migration files from `files/`, apply the kit to a scratch copy of the project, run `makemigrations rooms` there to regenerate them, and copy them back. Then `kit.py rebuild-manifests` and `kit.py verify`. The two later kits depend on these models and must be re-verified.
