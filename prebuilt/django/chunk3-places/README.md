# Kit: chunk3-places

**Is:** all of plan chunk 3 (Tasks 6 and 7): list, create, open, rename and delete a place, with the owner check.
**Needs:** `chunk2-models` applied first.
**Result when laid on the project with chunk 2 (16 Nov 2026):** 99 tests, all pass (78 before, 21 new). The plan expected 96; three tests were added, listed below.

## Why it was safe to build early

The plan lists no builder decision for this chunk. "Each user sees only their own places" is in the approved design. The four calls the plan makes (404 for someone else's place; delete asks first; a rename keeps the address; a logged-in person at `/` goes to their places) still have to be read out before this goes in.

## What is in `files/`

| File | New or replaces | What it is |
| --- | --- | --- |
| `rooms/access.py` | new | `get_own_place(user, slug)`: the one line that is the privacy rule |
| `rooms/forms.py` | new | `PlaceForm`: one field, `name` |
| `rooms/views.py` | replaces | `home` (now redirects a logged-in user), `place_list`, `place_create`, `place_detail`, `place_edit`, `place_delete` |
| `rooms/urls.py` | replaces | `/places/`, `/places/new/`, `/places/<slug>/`, `.../edit/`, `.../delete/` |
| `rooms/models.py` | replaces chunk 2's | Adds `Place.get_absolute_url()`. Nothing else differs; no migration |
| `rooms/templates/rooms/place_list.html`, `place_form.html`, `place_detail.html`, `place_confirm_delete.html` | new | The four pages. `place_form.html` serves both "new" and "rename" |
| `rooms/templates/rooms/home.html` | replaces | One sentence changed, so the page does not claim less than exists |
| `static/css/site.css` | replaces | One block added at the end for list pages and a delete button. Nothing above it changed |
| `rooms/tests/test_places.py` | new | 20 tests |
| `rooms/tests/test_home.py` | replaces | One test added: a logged-in person at `/` is sent to `/places/` |

## Calls made here that the plan did not spell out

1. **Three extra tests:** a request that names another user as `owner` is ignored; a place named "New" opens at `/places/new-2/` while `/places/new/` is still the create page (the plan's review focus 1, checked through the pages); the place page has both section headings.
2. **Page wording.** List page heading "Your places", button "New place", empty text "No places yet. A place is one room you want to keep." The delete page says "Delete this place?", lists "1 room video" and "2 photos", and says it cannot be undone. The rename page says the address does not change.
3. **A "← Your places" link** at the top of a place's page. The header's "Memory Room" link also leads there for a logged-in person.
4. **Dates are shown as "16 Nov 2026".**
5. **`home.html`'s note** now reads: "Today you can make an account and keep a list of your places. Room videos and photos come next. The 3D room is not built yet."
6. **Delete is a link to a page with a red button**, not a button on the place page, so nothing is deleted by one slip of a thumb.

## Not checked

Nothing was opened in a browser. The pages were only requested by the tests. How they look on a phone is unseen; the walk-through is the first look.

## Applying it

Follow "How to use a kit" in `prebuilt/README.md` with the name `chunk3-places`. No migration is needed, but running `migrate` is harmless. Expect **99** tests. Then the plan's **Walk through (chunk 3)** and the Record step with `system-map-section.md`.

## If it no longer fits

Most likely cause: `static/css/site.css`, `rooms/templates/rooms/home.html` or `rooms/tests/test_home.py` was edited in the project after 16 Nov. For each, the kit's change is small and at a known spot:

- `site.css`: everything from the comment `/* Pages that list things` to the end of the file is new. Append that block to the project's file.
- `home.html`: only the `<p class="note">` text differs.
- `test_home.py`: only `test_home_redirects_when_logged_in` was added, after `test_unknown_address_is_a_404`.
- `rooms/models.py`: only `get_absolute_url` and the `reverse` import were added to chunk 2's file.

Copy the merged file over the kit's version, then `kit.py verify`. (Run `rebuild-manifests` only while no kit is applied.)
