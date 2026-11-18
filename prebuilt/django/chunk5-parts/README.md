# Kit: chunk5-parts

**Is:** the part of plan chunk 5 (Task 10) that comes out the same whatever the builder decides for **D2** (how photos are added) and **D3** (who can fetch a photo file). It is **not** chunk 5. No page, no address and no template is in it.
**Needs:** `chunk2-models`, `chunk3-places`, `chunk4-video` applied first.
**Result when laid on the project with the other three (16 Nov 2026):** 143 tests, all pass (123 before, 20 new).

## When to apply it

At the start of the chunk 5 session, **after** the builder has answered D2 and D3 in that session's Decide step. Applying it earlier does no harm (nothing calls the new code) but there is no reason to.

Then build the rest of chunk 5 from the plan as usual. What is left for that session:

| Plan item | State |
| --- | --- |
| `rooms.photos.photo_taken_on` | **Here** |
| `rooms.validators.validate_photo` and `MAX_PHOTO_BYTES` | **Here** |
| `rooms.forms.MemoryForm` (caption, taken_on) | **Here** |
| `MultipleImageField`, `MemoryUploadForm`, `MAX_PHOTOS_PER_UPLOAD` | Not here: only exists under D2 option a |
| `get_own_memory`, every memory view, address and template, the photo grid | Not here: shaped by D2 and D3 |
| Tests in the plan's `MemoryFormTests` that upload through the multi-photo form, all of `MemoryPageTests` and `MemoryEditTests` | Not here |

The chunk 5 session adds its tests to the same file, `rooms/tests/test_memories.py`.

## What is in `files/`

| File | New or replaces | What it is |
| --- | --- | --- |
| `rooms/photos.py` | new | `photo_taken_on(file)`: the capture date inside a photo, or `None`. Never raises; leaves the file rewound |
| `rooms/validators.py` | replaces chunk 4's | Adds `validate_photo(file)`: size, then "Pillow can open it and it is JPEG, PNG or WebP" |
| `rooms/forms.py` | replaces chunk 4's | Adds `MemoryForm` at the end |
| `config/settings.py` | replaces chunk 4's | Adds `MAX_PHOTO_BYTES = 20 MB` at the end |
| `rooms/tests/test_memories.py` | new | 20 tests: 7 on reading dates, 8 on the photo check, 5 on the form |

## Calls made here (all from the plan's chunk 5 list unless marked)

- JPEG, PNG and WebP only; 20 MB each. HEIC gets the message "Upload JPEG, PNG or WebP photos. HEIC is not supported yet."
- The date is read from the capture-date field, falling back to the file-change date; anything unreadable gives no date.
- *Not in the plan:* the photo check ignores the file's name and goes by content alone, so a real JPEG with an odd name is accepted. A test shows it.
- *Not in the plan:* a camera date of all zeros (a camera with no clock set) gives no date. A test shows it.
- *Not in the plan:* `MemoryForm`'s date label is "Taken on" and it uses the phone's date picker, like `ScanForm`.

## Not checked

No photo from a real phone has been through `photo_taken_on`. The tests use 8×8 images made by Pillow with a date written the way cameras write it. The plan's chunk 5 walk-through (real photos, one screenshot, one HEIC if the phone has one) is where that is found out.

## If it no longer fits

Each of the three replaced files only gains a block at its end (plus one import line at the top of `validators.py` and one name added to an import in `forms.py`). Append the same blocks to the project's versions.
