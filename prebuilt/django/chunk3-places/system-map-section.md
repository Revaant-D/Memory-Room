<!-- DRAFT for docs/system-map.md. Written 16 Nov 2026 before the chunk was applied.
     Before pasting: check it against the applied code, fix the test count if it moved,
     update "What exists today", "Last updated", the layout block and the test total at
     the top of the system map, and delete this comment. -->

## Piece 4: Places

### What it does

Lets a logged-in person keep a list of places: create one, open it, rename it, delete it. A person sees only their own. This is the app's first complete loop from a form, through a view, into the database and back onto a page.

| Address | Page | View |
| --- | --- | --- |
| `/` | Landing page; a logged-in person is sent on to `/places/` | `home` |
| `/places/` | Your places | `place_list` |
| `/places/new/` | New place | `place_create` |
| `/places/<slug>/` | One place, with its "Room scans" and "Photos" sections | `place_detail` |
| `/places/<slug>/edit/` | Rename | `place_edit` |
| `/places/<slug>/delete/` | Asks first, then deletes | `place_delete` |

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/access.py` | `get_own_place(user, slug)`: the owner check |
| `rooms/forms.py` | `PlaceForm`: the one field `name` |
| `rooms/views.py` | One function per page |
| `rooms/urls.py` | The table above |
| `rooms/models.py` | `Place.get_absolute_url()` |
| `rooms/templates/rooms/` | `place_list.html`, `place_form.html` (new and rename), `place_detail.html`, `place_confirm_delete.html` |
| `rooms/tests/test_places.py` | 20 tests |

### How one request flows

Creating a place called "Dorm Room 214":

1. The browser sends `POST /places/new/` with `name` and the hidden security token.
2. `config/urls.py` → `rooms/urls.py`. The line for `places/new/` is above the line for `places/<slug>/`, so "new" is not read as a place's address.
3. `@login_required` on `place_create` checks the session. A logged-out visitor is sent to `/accounts/login/?next=/places/new/` and returns here after logging in.
4. `PlaceForm(request.POST).is_valid()` checks the name: not blank, at most 80 characters.
5. The view sets `form.instance.owner = request.user`. The owner is never read from the request, so nobody can create a place in another person's name.
6. `form.save()` → `Place.save()` → `unique_slug()` makes `dorm-room-214` → the row is inserted.
7. "Place created." is stored to show once, and the view redirects to `/places/dorm-room-214/`.
8. `place_detail` → `get_own_place(request.user, "dorm-room-214")` → `place_detail.html`.

### The owner check

```python
def get_own_place(user, slug):
    return get_object_or_404(Place, owner=user, slug=slug)
```

Every view that needs a place calls this and nothing else. It asks the database for the slug **and** the owner together, so another person's place is not found at all. The answer is 404, the same as for an address that does not exist, never 403: a 403 would confirm that the address belongs to someone.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Each user sees only their own places | **Builder** (the approved design) | The product is private by default |
| Another user's place answers 404, not 403 | Claude, 16 Nov | Nobody can learn which addresses are taken |
| The check lives in one function in `rooms/access.py` | Claude, 16 Nov | One place to read, one place to get right; a view cannot forget part of it |
| Deleting asks first, on a page that counts what will go | Claude, 16 Nov | It removes videos and photos for good |
| Renaming does not change the address | Claude, 16 Nov | Old links keep working |
| A logged-in person at `/` is sent to their places | Claude, 16 Nov | The landing page has nothing for them |
| The owner is set in the view, and `owner` is not a form field | Claude, 16 Nov | A crafted request cannot choose the owner. A test proves it |

### How to change it

- **Add something a person types when creating a place:** add the field to `Place`, migrate, and add it to `fields` in `PlaceForm`. The pages draw it without further changes.
- **Change who can open a place** (sharing, say): `get_own_place` is the only spot. Every page follows.
- **Change an address:** `rooms/urls.py`. Templates and redirects use the names (`place_detail`), so they follow; tests that spell out addresses will need the same change.

### Known gaps

- No paging: a person with hundreds of places gets one long list.
- A place cannot be moved to another user.
