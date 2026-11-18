# Kit: chunk4-video

**Is:** all of plan chunk 4 (Tasks 8 and 9): upload a room video to a place, see it listed with its status, delete it.
**Needs:** `chunk2-models` and `chunk3-places` applied first.
**Result when laid on the project with chunks 2 and 3 (16 Nov 2026):** 123 tests, all pass (99 before, 24 new). The plan expected 117 at this point; the difference is the 3 extra tests in chunk 3 and 3 extra here.

## Why it was safe to build early

The plan lists no builder decision for this chunk; the Scan model and "the video is kept for now" are in the approved §6. **But this chunk's calls carry numbers the plan says the builder may want to change.** Read them out before applying:

| Call | Value | Where to change it |
| --- | --- | --- |
| Accepted types | MP4 and MOV | `VIDEO_ENDINGS` in `rooms/validators.py`, and the `accept` attribute in `ScanForm` |
| Size limit | 500 MB (about three minutes at 1080p) | `MAX_VIDEO_BYTES` in `config/settings.py`. The message follows the setting |
| Filming date | Starts as today; cannot be in the future | `ScanForm.clean_taken_on` in `rooms/forms.py` |
| Status after upload | Stays "Uploaded"; the page says nothing builds the room yet | `place_detail.html` |
| Several scans per place | Yes, newest filming date first | `Scan.Meta.ordering` (chunk 2) |

## What is in `files/`

| File | New or replaces | What it is |
| --- | --- | --- |
| `rooms/validators.py` | new | `validate_video(file)`: ending, size, first bytes. `size_words()` for messages |
| `rooms/forms.py` | replaces chunk 3's | Adds `ScanForm` (video, taken_on) |
| `rooms/access.py` | replaces chunk 3's | Adds `get_own_scan(user, pk)` |
| `rooms/views.py` | replaces chunk 3's | Adds `scan_create`, `scan_delete`; `place_detail` now passes the place's scans |
| `rooms/urls.py` | replaces chunk 3's | Adds `/places/<slug>/scans/new/` and `/scans/<pk>/delete/` |
| `rooms/templates/rooms/scan_form.html`, `scan_confirm_delete.html` | new | The upload page and the delete confirmation |
| `rooms/templates/rooms/place_detail.html` | replaces chunk 3's | The "Room scans" section now lists scans and has an "Add a room video" button |
| `rooms/templates/rooms/home.html` | replaces chunk 3's | One sentence changed |
| `config/settings.py` | replaces chunk 1's | Adds `MAX_VIDEO_BYTES` at the end. Nothing above it changed |
| `rooms/tests/test_scans.py` | new | 24 tests |

## Calls made here that the plan did not spell out

1. **Three extra tests:** the size message takes its number from the setting; the video check leaves the file rewound (the plan requires this but listed no test); the upload page really has `enctype="multipart/form-data"`.
2. **`test_delete` also checks that the place's photos survive** deleting a video.
3. **The hidden second date input is switched off.** For a field whose starting value is "today", Django adds a hidden copy of the input to the page. Nothing uses it, so `ScanForm.__init__` turns it off. One line, explained in a comment.
4. **Wording.** Field labels "Room video" and "Filmed on". Help text: "Film at 1080p. One to two minutes is enough. MP4 or MOV." The upload page adds: "Walk slowly around the room once, filming every wall. A large video can take a few minutes to upload: keep this page open until it finishes." The delete page says the photos stay.
5. **A MOV file from a very old camera may be refused.** The first-bytes check looks for `ftyp` at bytes 4 to 8, which every phone writes. Some pre-2005 QuickTime files start differently.
6. **`home.html`'s note** now reads: "Today you can make an account, keep a list of your places and add a room video to each. Photos come next. The 3D room is not built yet."

## Not checked

- **No real video has been uploaded.** The tests use 64 bytes that begin like an MP4. Whether a 300 MB phone video uploads through the development server in reasonable time is unknown; the plan's walk-through step 1 is where that is found out. The builder should note how long it takes.
- Nothing was opened in a browser.
- The first-bytes check is a sanity check, not proof that the video plays or that the reconstruction step can read it.

## Applying it

Follow "How to use a kit" in `prebuilt/README.md` with the name `chunk4-video`. No migration. Expect **123** tests. Then the plan's **Walk through (chunk 4)** (it uses the builder's real room video) and the Record step with `system-map-section.md`.

## If it no longer fits

`config/settings.py` is the likely one if settings were touched after chunk 1: the kit only appends the "Upload limits" block at the end; append the same block to the project's file. For the files that replace chunk 3's versions, every addition is at the end of the file or is a clearly marked block (`# --- Room scans` in `views.py`; the two `scans` lines in `urls.py`; `get_own_scan` in `access.py`; `ScanForm` in `forms.py`).
