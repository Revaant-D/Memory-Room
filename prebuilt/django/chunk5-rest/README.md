# chunk5-rest: the rest of chunk 5, in four versions

**Is:** everything in plan chunk 5 (Tasks 10, 11, 12) that `chunk5-parts` left out: adding photos, the photo grid on a place's page, a photo's own page (caption, date, delete), and how a photo file is fetched. Built once for each answer to the builder's two open decisions.
**Needs:** `chunk2-models`, `chunk3-places`, `chunk4-video` and `chunk5-parts` applied first.
**Exactly one of the four folders is ever applied, and only after the builder has answered D2 and D3.**

## Why there are four

D2 (how photos are added) and D3 (who can fetch a photo file) are the builder's decisions and were open when this was built. Building only the recommended answers would have made them the cheap answers, which is a way of deciding for the builder. So all four combinations were built and tested to the same standard. None is "the" version. Do not tell the builder one is "already done"; they all are.

| Kit name | Folder | D2 | D3 | Whole suite | Deliberate breaks caught |
| --- | --- | --- | --- | --- | --- |
| `chunk5-D2a-D3a` | `D2a-D3a/` | a: many photos at once, captions afterwards | a: a view that checks the owner | 195 pass | 18 of 18 |
| `chunk5-D2b-D3a` | `D2b-D3a/` | b: one photo per form, caption on the form | a: a view that checks the owner | 195 pass | 16 of 16 |
| `chunk5-D2a-D3b` | `D2a-D3b/` | a: many photos at once, captions afterwards | b: open, hard-to-guess addresses | 192 pass | 17 of 17 |
| `chunk5-D2b-D3b` | `D2b-D3b/` | b: one photo per form, caption on the form | b: open, hard-to-guess addresses | 192 pass | 15 of 15 |

Numbers printed on 16 Nov 2026 by `kit.py verify --choice NAME` and `breakcheck.py --choice NAME`. The suite is 143 tests before any of these goes in. No version needs a migration. The two D2 columns having the same count is a coincidence.

Applying one after the other kits was also tried end to end on a throwaway copy (`chunk5-D2b-D3b`: applied, migrated, 192 pass, and `kit.py` then refused to apply a second version on top).

## What the two decisions change, in the code

Everything not listed here is identical in all four.

**D2: how photos are added**

| | a: many at once | b: one per form |
| --- | --- | --- |
| `rooms/forms.py` | `MultipleFileInput`, `MultipleImageField`, and `MemoryUploadForm` (a plain form with one field, `photos`) | `MemoryUploadForm` (a `ModelForm` on `photo`, `caption`, `taken_on`) |
| `views.memory_create` | Makes one `Memory` per file inside one transaction. "3 photos added." | Saves one `Memory`. "Photo added." |
| The date | Always read from the photo | Read from the photo only when the date box is left empty; a typed date wins |
| A bad file | Refuses the whole batch and names each bad file | Refuses the one file; the caption typed so far is kept on the form |
| `config/settings.py` | Adds `MAX_PHOTOS_PER_UPLOAD = 50` | Nothing added |
| Page wording | "Add photos" | "Add a photo" |
| `rooms/tests/test_memory_upload.py` | 23 tests | 23 different tests |

**D3: who can fetch a photo file**

| | a: owner-checked view | b: open addresses |
| --- | --- | --- |
| `Memory.photo_address()` in `rooms/models.py` | `/memories/<number>/photo/` | `/media/places/<id>/memories/<32 random characters>.jpg` |
| `views.memory_photo` and its line in `rooms/urls.py` | Present: checks login and owner, then sends the file with `Cache-Control: private, max-age=3600` | Absent |
| `config/urls.py` | Unchanged | Serves `/media/` with Django's `static()` helper, which only works while `DEBUG` is on |
| `config/settings.py` | Unchanged | The comment on `MEDIA_ROOT` is rewritten: photos are hard to find, not private |
| Someone with a photo's address, not logged in | Sent to the login page | **Gets the photo** (while `DEBUG` is on) |
| Another logged-in user | 404 | **Gets the photo** |
| A deployed site (`DEBUG` off) | Works as it is, slowly; later becomes time-limited bucket links | Shows no photos until a web server or bucket is set up to answer `/media/` |
| `rooms/tests/test_memory_files.py` | 8 tests | 5 tests, which record the trade-off above |

Under option b, room **videos** are reachable the same way as photos, since they live in the same folder. No page links to a video, but its address is no more private than a photo's.

## The same in all four

| File | What it is |
| --- | --- |
| `rooms/access.py` | Adds `get_own_memory(user, pk)` |
| `rooms/views.py` | Adds `memory_edit`, `memory_delete`; `place_detail` passes the place's photos |
| `rooms/urls.py` | `/places/<slug>/memories/new/`, `/memories/<number>/edit/`, `/memories/<number>/delete/` |
| `rooms/templates/rooms/memory_upload.html`, `memory_form.html`, `memory_confirm_delete.html` | The upload page, a photo's own page, and the delete confirmation |
| `rooms/templates/rooms/place_detail.html` | The "Photos" section becomes a grid; each photo links to its own page |
| `rooms/templates/rooms/home.html` | One sentence changed |
| `static/css/site.css` | One block added at the end: the grid, and one large photo |
| `rooms/tests/test_memory_pages.py` | 21 tests: the grid, a photo's page, delete, and who may do so |

## Calls made here that the plan did not spell out

Read these out with the plan's "Claude's calls" for chunk 5.

1. **Templates ask the photo for its address** (`{{ memory.photo_address }}`) and do not build it themselves. This keeps D3 in one method, and is the one line to change when photos move to a storage bucket.
2. **Tests are in three files by topic**, not all in `test_memories.py` as the plan has it: `test_memory_pages.py`, `test_memory_upload.py` (D2), `test_memory_files.py` (D3). `test_memories.py` keeps the tests from `chunk5-parts`.
3. **Under D2 a, each file is checked by `validate_photo` and not by Django's `ImageField`.** The plan said to run both. `validate_photo` already has Pillow open the file; running Django's check first would give an iPhone HEIC photo Django's generic "not a valid image" message, where the plan wants the plain "HEIC is not supported yet".
4. **Under D2 b, a date left empty is filled from the photo.** The plan did not say what option b does with the photo's own date.
5. **A photo's own page is the edit page.** Tapping a photo in the grid opens it large, with its caption and date boxes under it and a "Delete this photo" link. There is no separate view-only page.
6. **Extra tests beyond the plan's list**, among them: an edit request cannot swap the photo or move it to another place; deleting a photo removes its pins and leaves the scan; the saved file is byte-for-byte the uploaded one; the place page still loads when a photo's file has gone from disk; photos are listed newest first with undated ones last.
7. **Wording** on the pages, and the grid's look (squares, 140 px or wider, two per row on a phone).

## Known limits

- Under D2 a, if saving fails part-way through a batch (the disk fills, say), the database rows are rolled back but files already written stay on disk with no row pointing at them.
- No thumbnails: the grid loads each full-size photo and scales it down. Slow with many large photos. The plan lists this as a later improvement.
- Location data inside photos is kept as it is. The plan defers stripping it to the security work.
- A double tap on the upload button can upload twice. The plan's walk-through step 6 checks for exactly this.

## Not checked

Nothing was opened in a browser. No photo from a real phone was used: the tests use 8×8 images made by Pillow. How the multi-file picker behaves on Android and iPhone is unseen.

## Applying one

In the chunk 5 session, after the Decide step has the builder's answers to D2 and D3:

```powershell
.venv\Scripts\python.exe prebuilt\tools\kit.py verify --choice chunk5-D2a-D3a     # use the chosen name
.venv\Scripts\python.exe prebuilt\tools\kit.py apply chunk5-D2a-D3a --write
.venv\Scripts\python.exe manage.py test                                          # expect the number in the table
```

Then the plan's **Walk through (chunk 5)** and the Record step with `system-map-section.md` from this folder, which is written with both answers side by side and must be trimmed to the one chosen. The three folders not chosen can be deleted.

If the builder wants something that is none of the four (for example many at once **with** a caption box per photo), start from the nearest folder; the shared files above will not need to change.
