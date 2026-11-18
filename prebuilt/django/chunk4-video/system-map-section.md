<!-- DRAFT for docs/system-map.md. Written 16 Nov 2026 before the chunk was applied.
     Before pasting: check it against the applied code, fix the test count if it moved,
     add how long the builder's real upload took, update "What exists today",
     "Last updated", the layout block and the test total at the top of the system map,
     and delete this comment. -->

## Piece 5: Room video upload

### What it does

Lets a person add a filmed video of a room to a place, see it listed with its filming date and status, and delete it. A place can hold several videos; the most recently filmed is listed first.

**Nothing builds the 3D room yet.** An uploaded video stays at "Uploaded", and the page says so. Turning a video into a room is a separate piece, run by hand outside the app for now.

| Address | Page | View |
| --- | --- | --- |
| `/places/<slug>/scans/new/` | Add a room video | `scan_create` |
| `/scans/<number>/delete/` | Asks first, then deletes | `scan_delete` |

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/validators.py` | `validate_video`: the three checks on the file |
| `rooms/forms.py` | `ScanForm`: the video and the filming date |
| `rooms/access.py` | `get_own_scan(user, pk)`: the owner check for a scan |
| `rooms/views.py` | `scan_create`, `scan_delete`; `place_detail` lists the scans |
| `rooms/templates/rooms/` | `scan_form.html`, `scan_confirm_delete.html`, and the "Room scans" section of `place_detail.html` |
| `config/settings.py` | `MAX_VIDEO_BYTES` |
| `rooms/tests/test_scans.py` | 24 tests |

### How one request flows

Uploading a room video to "Dorm":

1. The browser sends `POST /places/dorm/scans/new/` as a multipart request: the form has `enctype="multipart/form-data"`, which is what lets it carry a file. As a large file arrives, Django writes it to a temporary file on disk, not into memory.
2. `rooms/urls.py` → `views.scan_create` → `@login_required` → `get_own_place(request.user, "dorm")`. Someone else's place is a 404 before the file is looked at.
3. `ScanForm(request.POST, request.FILES).is_valid()` runs `validate_video` on the file and checks the date is not in the future.
4. The view sets `form.instance.place` from the address, then `form.save()`.
5. `scan_video_path` (in `rooms/models.py`) chooses the stored name, `places/<place id>/scans/<32 random characters>.mp4`, and the file moves into `media/`.
6. The row is inserted with status `uploaded`. "Room video added." is stored, and the view redirects to the place's page, which now lists the scan.

### The three checks on a video

In this order, cheapest first (`rooms/validators.py`):

| Check | Refused with |
| --- | --- |
| The file name ends in `.mp4` or `.mov`, any case | "Upload an MP4 or MOV video." |
| The file is at most `MAX_VIDEO_BYTES` (500 MB) | "This video is too large. The limit is 500 MB." |
| Bytes 4 to 8 of the file are `ftyp`, as in every MP4 and modern MOV | "This file is not a video the app can read." |

An empty file is refused by Django's own file field before these run.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| The video is kept after upload | **Builder** (approved §6) | It is the source the room is built from, and can be rebuilt from |
| MP4 and MOV only | Claude, 16 Nov | They are what Android and iPhone cameras write |
| Checked by name and by first bytes | Claude, 16 Nov | The name is whatever the sender says. The first bytes catch a photo or a document renamed by mistake. It is a sanity check, not proof the video plays |
| 500 MB limit | Claude, 16 Nov | About three minutes at 1080p (roughly 130 MB a minute on the builder's phone); one to two minutes is enough for a room |
| The filming date starts as today and cannot be in the future | Claude, 16 Nov | Most videos are uploaded the day they are filmed; an old one can be back-dated |
| A place can hold several scans | Claude, 16 Nov | A room can be filmed again later; the model already allows it |
| `ScanForm` declares its own file field | Claude, 16 Nov | Django's generated one refuses a file whose original name is over 100 characters, and the original name is never stored |
| A scan is found by its number, a place by its word | Claude, 16 Nov | A scan has no name to make a word from |

### How to change it

- **Change the size limit:** `MAX_VIDEO_BYTES` in `config/settings.py`. The message updates itself.
- **Accept another video type:** add its ending to `VIDEO_ENDINGS` in `rooms/validators.py` and its type to the `accept` attribute in `ScanForm`. Check what its first bytes look like before relying on the third check.
- **Start a build when a video arrives:** the line after `form.save()` in `scan_create` is where that hand-off would go.

### Known gaps

- No progress bar. A large upload shows only the browser's own loading indicator.
- If the upload is interrupted, the person starts again.
- A double tap on the upload button can send the video twice.
- The checks do not prove the file is a playable video.
