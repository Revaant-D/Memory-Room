<!-- DRAFT for docs/system-map.md. Written 16 Nov 2026 before D2 and D3 were decided.
     It carries BOTH answers to each, marked [D2 a] / [D2 b] and [D3 a] / [D3 b].
     Before pasting: delete the lines for the answers NOT chosen, write the builder's
     own reasons into the two "Builder" rows, check everything against the applied
     code, fix the test counts, update the top of the system map, delete this comment. -->

## Piece 6: Photos

### What it does

Lets a person add photos to a place, see them in a grid, give each a caption and a date, and delete them. The app calls a photo with its caption and date a **memory**.

- [D2 a] Many photos are picked in one go. Captions are added afterwards, photo by photo.
- [D2 b] Photos are added one at a time, each with its caption and date on the same form.
- [D3 a] A photo file can only be fetched by its owner, logged in.
- [D3 b] A photo file can be fetched by anyone who has its address. The address is long and random, so it cannot be guessed.

| Address | Page | View |
| --- | --- | --- |
| `/places/<slug>/memories/new/` | Add photos | `memory_create` |
| `/memories/<number>/edit/` | One photo, large, with its caption and date | `memory_edit` |
| `/memories/<number>/delete/` | Asks first, then deletes | `memory_delete` |
| [D3 a] `/memories/<number>/photo/` | The photo file itself | `memory_photo` |
| [D3 b] `/media/places/<id>/memories/<random>.jpg` | The photo file itself | Django's file serving, while `DEBUG` is on |

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/photos.py` | `photo_taken_on`: reads the capture date from inside a photo |
| `rooms/validators.py` | `validate_photo`: size, and "is really a JPEG, PNG or WebP" |
| `rooms/forms.py` | `MemoryUploadForm` (adding) and `MemoryForm` (caption and date). [D2 a] also `MultipleImageField` |
| `rooms/access.py` | `get_own_memory(user, pk)` |
| `rooms/views.py` | `memory_create`, `memory_edit`, `memory_delete`. [D3 a] `memory_photo` |
| `rooms/models.py` | `Memory.photo_address()`: the address pages use to show a photo |
| `rooms/templates/rooms/` | `memory_upload.html`, `memory_form.html`, `memory_confirm_delete.html`, and the "Photos" section of `place_detail.html` |
| `config/settings.py` | `MAX_PHOTO_BYTES`. [D2 a] `MAX_PHOTOS_PER_UPLOAD` |
| [D3 b] `config/urls.py` | Serves `/media/` while `DEBUG` is on |
| `rooms/tests/` | `test_memories.py`, `test_memory_pages.py`, `test_memory_upload.py`, `test_memory_files.py` |

### How one request flows

[D2 a] Uploading three photos to "Dorm":

1. `POST /places/dorm/memories/new/`, a multipart request carrying three files under the one name `photos`.
2. `views.memory_create` → `@login_required` → `get_own_place`.
3. `MemoryUploadForm.is_valid()` → `MultipleImageField.clean`: at most 50 files; each file must be non-empty and pass `validate_photo`. Every failure is collected as "file name: reason". One bad file refuses the whole upload.
4. Inside one database transaction, for each file: `photo_taken_on(file)` reads its date, and a `Memory` row is created. `memory_photo_path` picks the stored name.
5. "3 photos added." and a redirect to the place's page.

[D2 b] Uploading one photo to "Dorm":

1. `POST /places/dorm/memories/new/` with the file, a caption and a date (either may be empty).
2. `views.memory_create` → `@login_required` → `get_own_place`.
3. `MemoryUploadForm.is_valid()` runs `validate_photo` on the file and checks the caption's length and that the date is not in the future.
4. The view sets the place from the address. If no date was typed, it takes the one inside the photo.
5. `form.save()` stores the file and the row. "Photo added." and a redirect to the place's page.

Then, in both: the place's page lists the photos, and the browser asks for each image.

- [D3 a] Each `<img>` points at `/memories/<number>/photo/`. `views.memory_photo` → `@login_required` → `get_own_memory` (404 for anyone else) → the file is sent with `Cache-Control: private, max-age=3600`. A row whose file has gone from disk gives 404.
- [D3 b] Each `<img>` points at the file's own address under `/media/`. No view of ours runs; nothing checks who is asking.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| D2: how photos are added: **(a or b)** | **Builder, (date)** | (the builder's reason) |
| D3: who can fetch a photo file: **(a or b)** | **Builder, (date)** | (the builder's reason) |
| JPEG, PNG and WebP only, 20 MB each | Claude, 16 Nov | They are what browsers show and Pillow reads. HEIC gets a plain message |
| A photo is judged by its content, not its name | Claude, 16 Nov | The name is whatever the sender says |
| [D2 a] At most 50 photos per upload; one bad file refuses the batch | Claude, 16 Nov | Simple to explain. Saving the good ones and skipping the bad is friendlier and is a later improvement |
| The date is read from inside the photo when it has one | Claude, 16 Nov | Saves typing; it can be edited afterwards |
| Pages get a photo's address from `Memory.photo_address()` | Claude, 16 Nov | One line to change when photos move to a storage bucket |
| Location data inside photos is left alone for now | Claude, 16 Nov | It belongs with the security work before deployment |
| The grid shows full-size photos scaled down | Claude, 16 Nov | No thumbnail code yet; fine for tens of photos |

### How to change it

- **Change a limit:** `MAX_PHOTO_BYTES` (and `MAX_PHOTOS_PER_UPLOAD`) in `config/settings.py`. Messages and help text follow.
- **Accept another photo type:** `PHOTO_FORMATS` in `rooms/validators.py`, and the `accept` attribute on the upload field. HEIC needs an extra library.
- **Change where photos are fetched from:** `Memory.photo_address()`.
- **Add a field to a memory:** the model, a migration, and `fields` in `MemoryForm`.

### Known gaps

- No thumbnails.
- Location data stays inside uploaded photos.
- A double tap on the upload button can upload twice.
- [D2 a] If saving fails part-way through a batch, files already written are left on disk without rows.
- [D3 b] Photos and videos are not private: anyone given an address can open the file. On a deployed site nothing serves `/media/` until a web server or bucket is set up.
- [D3 a] Every image request runs Python, which is fine at this size and slow at a large one.
