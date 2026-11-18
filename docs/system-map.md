# Memory Room: system map

What has been built, where it lives, how a request moves through it, and why each decision was made. One section per piece. Each section is added when its piece is built, so anything described here exists and has been run.

**Last updated:** 18 Nov 2026: the Dollhouse look (piece 10), which replaces piece 9's page; before that chunk 5 (photos, piece 7), the room import (piece 8) and the 3D room page (piece 9).

## What exists today

A Django project that runs. A person can sign up, log in and log out; keep a list of places (create, open, rename, delete); add or delete a room video on each place; and add many photos to a place at once, caption them, change their dates and delete them. A room built in Colab is attached to its scan with `manage.py import_room` (piece 8) and then opens as a 3D page with its photos as dots (piece 9). Nobody can open another person's places, photos or rooms. The four tables (Place, Scan, Memory, Pin) exist with their rules and are editable in `/admin/`. Since 18 Nov (piece 10) the whole site has the Dollhouse look: a place with a built room is that room, and a photo is placed by tapping the floor where it was taken; the app writes those pins.

A Colab notebook that builds the 3D room from a room video exists (piece 6) but has not been run on a real video yet.

Pieces 3, 4 and 5 were applied on 17 Nov, and piece 7 on 18 Nov, without the builder present, at their request. Their calls have not been read out yet and their walk-throughs are owed (for the first draft, one combined walk-through). Each section says so at its top.

## Running it

All commands are run from the project folder, in PowerShell. They call the project's own Python by its path, so nothing needs activating.

| To do this | Run this |
| --- | --- |
| Start the site | `.venv\Scripts\python.exe manage.py runserver`, then open `http://127.0.0.1:8000/` |
| Run every test | `.venv\Scripts\python.exe manage.py test` |
| Run one app's tests | `.venv\Scripts\python.exe manage.py test accounts` |
| Make an admin login | `.venv\Scripts\python.exe manage.py createsuperuser`, then open `/admin/` |
| Apply database changes | `.venv\Scripts\python.exe manage.py migrate` |
| Open a Python prompt with the app loaded | `.venv\Scripts\python.exe manage.py shell` |

There are 240 tests. All 240 passed on 18 Nov 2026, after the fixes from the code review of 18 Nov (see "Code review, 18 Nov" near the end).

| To do this | Run this |
| --- | --- |
| Attach a room built in Colab to a scan | `.venv\Scripts\python.exe manage.py import_room <scan number> <room folder or .zip>` (piece 8) |

On 17 Nov the app was also checked with real HTTP requests against a running server (a throwaway copy with its own database): 20 of 20 checks passed. They covered sign-up, creating, renaming and deleting a place, the numbered and reserved addresses, a stand-in video upload and two refused files, another user getting a 404, a logged-out visitor sent to login, a POST without the security token refused, and `media/` empty after the deletes. No real phone video was used, and nothing was looked at in a browser.

## The layout

```
memory-room/
├─ manage.py                  Django's command-line entry point
├─ requirements.txt           the exact library versions
├─ config/                    the project: settings and the top of the address map
│  ├─ settings.py
│  ├─ secret.py               finds or creates the secret key
│  ├─ urls.py
│  └─ tests.py                tests for secret.py
├─ templates/                 pages shared by the whole site
│  ├─ base.html               the frame every page sits in
│  ├─ includes/form_fields.html   draws any form's fields the same way
│  ├─ 404.html                "page not found"
│  └─ 500.html                "something went wrong"
├─ static/css/site.css        the one stylesheet
├─ static/viewer/             the 3D viewer (room3d.js, roomgeom.js, loaders.js) and three.js in vendor/
├─ static/site/               one script per page (landing, places, room, backdrop) and views.js
├─ accounts/                  the user, sign-up, login, logout
└─ rooms/                     places, scans, memories, pins
   ├─ models.py               the four tables and their rules
   ├─ slugs.py                the word in a place's address
   ├─ signals.py              removes files from disk when their row goes
   ├─ access.py               the owner checks: every page that loads a place, scan or photo goes through here
   ├─ validators.py           the checks on an uploaded video or photo
   ├─ photos.py               reads the date a photo was taken from inside the file
   ├─ roomfolder.py           reads and checks a room built in Colab (folder or zip)
   ├─ management/commands/import_room.py   attaches a built room to a scan
   ├─ forms.py, views.py, urls.py, admin.py
   ├─ templates/rooms/        the pages
   ├─ migrations/
   └─ tests/
```

Beside the app: `ai/` holds the AI part (piece 6), which Django does not import; `ai/README.md` describes it.

Made when the app runs and never put in git: `.venv/` (the libraries), `db.sqlite3` (the database), `.secret_key`, `media/` (uploads), and `ai/dist/` (the code zip for Colab).

---

## Piece 1: Project and settings

### What it does

Holds everything Django needs to know about the project, and sends each incoming address to the right app.

### Where the code is

| File | What it is |
| --- | --- |
| `config/settings.py` | Every setting, grouped under headings: security, apps, database, accounts, language and time, files |
| `config/secret.py` | One function, `load_secret_key`, that returns the secret key |
| `config/urls.py` | Three lines: `/admin/` to Django's admin, `/accounts/...` to the accounts app, everything else to the rooms app |
| `templates/base.html` | The page frame: the header (site name; who is logged in; log in, sign up or log out), one-time messages, and a space each page fills |
| `templates/includes/form_fields.html` | Draws a form's fields: label, errors, input, help text. Every form on the site uses it |
| `static/css/site.css` | The styling. Written for a phone first; follows the device's light or dark setting |

### How one request flows

Opening `http://127.0.0.1:8000/`:

1. Django passes the request through the list in `MIDDLEWARE` (in `settings.py`), top to bottom. The ones that matter here: the session middleware reads the `sessionid` cookie, and the authentication middleware uses it to set `request.user` (a real user, or an anonymous one).
2. `config/urls.py` is read from the top. `/` does not start with `admin/` or `accounts/`, so it falls to the last line, which hands over to `rooms/urls.py`.
3. `rooms/urls.py` matches the empty path to `views.home`.
4. `rooms/views.py: home` renders `rooms/templates/rooms/home.html`.
5. That template starts with `{% extends "base.html" %}`, so Django draws `base.html` and puts the home page's content into its `content` block. The header checks `user.is_authenticated` to choose what to show.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Django 5.2, not 6.1 | Claude, 16 Nov | 5.2 is the long-term-support line (to April 2028), the technical design names Django 5, and most teaching material matches it |
| Two apps, `accounts` and `rooms` | Claude, 16 Nov | Sign-up code and room code stay apart. The design named only `rooms` |
| The secret key is never in git | Class rule; method by Claude, 16 Nov | It comes from the `DJANGO_SECRET_KEY` environment variable, or from `.secret_key`, which the app creates on first run. A fresh clone therefore runs with no set-up, and no key is ever committed |
| The key is made with Python's `secrets` module, not Django's helper | Claude, 16 Nov | `secret.py` runs while the settings are still loading. Using only the standard library means it cannot depend on settings that do not exist yet |
| A key file with a stray byte-order mark still works; one in the wrong encoding gives a clear message | Claude, 16 Nov | Found in review. PowerShell 5 and Notepad both write files this way, and the alternative was a crash at start-up with an unreadable error |
| Debug mode is on unless `DJANGO_DEBUG` is set to something other than `1` | Claude, 16 Nov | Convenient locally. A deployed site sets `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` lists the host names the site answers to | Claude, 16 Nov | With debug off, Django refuses every request unless its host is listed. Without this setting, `DJANGO_DEBUG=0` would make the site unusable |
| Time zone `America/Chicago` | Claude, 16 Nov | Where the builder is. Times are stored in UTC and shown in this zone |
| SQLite and local disk | Builder, 16 Nov | Simplest until deployment |
| Function views, not class-based views | Claude, 16 Nov | Every step of a request is visible in one function, which makes the code easier to trace and explain |
| Django's built-in test runner, not pytest | Claude, 16 Nov | Nothing extra to install |
| One hand-written stylesheet, no framework, no JavaScript | Claude, 16 Nov | Small enough to read in one sitting |
| Our own "page not found" and "something went wrong" pages | Claude, 16 Nov | Opening another person's place will show the not-found page, so it should look like part of the site. The error page uses no template tags and no data, because it is drawn when something is already broken |
| Tests use a fast password hasher | Claude, 16 Nov | Real hashing is slow on purpose; with it the 50 tests took 15 seconds, without it under half a second. Only tests are affected: the check is `"test" in sys.argv` in `settings.py` |
| Uploaded files will not be reachable at `/media/` | Claude, 16 Nov (the builder decides the photo-serving question, D3, in chunk 5) | `MEDIA_ROOT` is set but no address serves it. Uploads are meant to be private |

### How to change it

- **A setting:** edit `config/settings.py`. Each group has a comment saying what it is for.
- **The look:** edit `static/css/site.css`. The colours are the variables at the top; the dark-mode values are just below them.
- **The header or the page frame:** edit `templates/base.html`. Every page changes at once.
- **A new library:** install it with `.venv\Scripts\python.exe -m pip install <name>`, then rewrite `requirements.txt` from `pip freeze`. Save the file as UTF-8.
- **Rotating the secret key:** delete `.secret_key`. A new one is made on the next start, and everyone is logged out.

---

## Piece 2: Accounts

### What it does

Lets a person create an account with a username and a password, log in, and log out. Every later piece depends on knowing who is logged in.

### Where the code is

| File | What it is |
| --- | --- |
| `accounts/models.py` | `User`: Django's own user, declared in our code with nothing added |
| `accounts/forms.py` | `SignupForm`: Django's sign-up form, told to make our `User` and to ask only for a username |
| `accounts/views.py` | `signup`: the one view written here |
| `accounts/urls.py` | `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`. Login and logout use Django's own views |
| `accounts/admin.py` | Puts users in the admin site |
| `accounts/templates/registration/` | `signup.html` and `login.html` |
| `accounts/migrations/0001_initial.py` | Creates the `accounts_user` table |
| `accounts/tests/test_accounts.py` | 29 tests |

### How one request flows

Signing up as `ana`:

1. The browser sends `POST /accounts/signup/` with `username`, `password1`, `password2` and a hidden `csrfmiddlewaretoken`.
2. The CSRF middleware compares that token with the `csrftoken` cookie. If the token is missing or wrong, the request stops here with a 403. This is what stops another website from submitting the form on a person's behalf.
3. `config/urls.py` → `accounts/urls.py` → `views.signup`.
4. `signup` builds `SignupForm(request.POST)` and calls `form.is_valid()`. That checks: the username uses only letters, digits and `@ . + - _`; nobody has that username, ignoring upper and lower case; the two passwords match; and the password passes the four rules in `AUTH_PASSWORD_VALIDATORS` (not too short, not too common, not all digits, not too like the username).
5. If anything fails, the same page is drawn again with the errors next to the fields. The passwords are not sent back.
6. If all is well, `form.save()` hashes the password and inserts a row into `accounts_user`.
7. `login(request, user)` starts a session: a row in the `django_session` table and a `sessionid` cookie that points to it.
8. `messages.success(...)` stores "Welcome, ana." to be shown once on the next page.
9. The view answers with a redirect to `/`. The browser follows it, and `base.html` now shows the username and a "Log out" button.

Logging out is `POST /accounts/logout/`, sent by the button in the header. Django's `LogoutView` deletes the session and redirects to `/`.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Our own `User` class, identical to Django's (D1, option b) | **Builder, 16 Nov** | Every other table points at the user table, and Django makes it very hard to swap the user class once real accounts exist. Owning the class from the start means a field can be added later with an ordinary migration. It had to be decided before the first migration |
| Sign-up asks only for a username and a password | Claude, 16 Nov | Collect as little as possible. The cost: with no email address there is no password reset yet |
| The sign-up form lists its fields explicitly | Claude, 16 Nov | A field not in the list, such as `is_staff`, cannot be set by whoever fills in the form. A test proves it |
| Logging out is a button that sends a POST, not a link | Django 5 requires it | A link or an image on another site cannot log a person out |
| A logged-in person who opens the sign-up or login page is sent to the home page | Claude, 16 Nov | Those pages have nothing to offer them |
| After login, a person returns to the page they were trying to reach, unless that page is on another site | Django's `LoginView` | Prevents a crafted link from sending someone to a look-alike site after they log in |
| The sign-up view is marked `never_cache` and its passwords are marked sensitive | Claude, 16 Nov | Browsers do not keep a copy of the page, and passwords stay out of error reports |

### How to change it

- **Add a field to the user** (a display name, say): add it to `User` in `accounts/models.py`, run `makemigrations` and `migrate`, and add it to `fields` in `SignupForm` if people should fill it in at sign-up.
- **Change the password rules:** edit `AUTH_PASSWORD_VALIDATORS` in `config/settings.py`.
- **Change where people land after logging in or out:** `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` in `config/settings.py`.

### Known gaps

- No password reset, because no email address is collected.
- No limit on repeated login or sign-up attempts.
- Usernames are compared exactly at login: `Ana` cannot log in as `ana`. Sign-up does refuse a new `Ana` when `ana` exists.

---

## Piece 3: Data model

**Status, 17 Nov 2026:** applied from `prebuilt/django/chunk2-models` while the builder was away, at their request ("I am not able to give time right now ... want you to start working"). The calls below have not yet been read out to the builder, and the plan's walk-through for chunk 2 is still owed. Either may change this piece.

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

---

## Piece 4: Places

**Status, 17 Nov 2026:** applied from `prebuilt/django/chunk3-places` while the builder was away, at their request ("I am not able to give time right now ... want you to start working"). The calls below have not yet been read out to the builder, and the plan's walk-through for chunk 3 is still owed. Either may change this piece.

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

---

## Piece 5: Room video upload

**Status, 17 Nov 2026:** applied from `prebuilt/django/chunk4-video` while the builder was away, at their request ("I am not able to give time right now ... want you to start working"). The calls below have not yet been read out to the builder, and the plan's walk-through for chunk 4 is still owed. Either may change this piece.

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

---

## Piece 6: Building the room (Colab notebook)

**Status, 18 Nov 2026:** built and rehearsed with a stand-in model; **first real run on 18 Nov** (`room-20261118-1342`), which found a levelling bug that was fixed the same day (decision below). Its full account is `ai/README.md`; this section is the summary.

### What it does

Turns one room video into a 3D room. The video and a zip of the code go in a Google Drive folder; `ai/build_room_colab.ipynb` runs in Colab on a free GPU and writes a room folder back to Drive. Django does not call it: for the first draft the room is built by hand, outside the app.

### How one run flows

1. `roompipe.frames.extract_frames`: the video is cut into 60 stretches; the sharpest frame of each is kept.
2. `roompipe.model.run_mapanything`: one MapAnything pass over the frames (Apache weights, revision `00f9c24`). It returns a camera for every frame and a 3D point for every pixel. The least certain fifth of the points is dropped.
3. `roomgeom.level.level_room`: a first guess at "up" from how the phone was held; then the floor, found as the lowest flat layer below the phone (`floor_layer`), and its own plane (`floor_plane`), which gives the final "up". The floor goes to z = 0; the points are thinned to one per 2 cm; about 20 anchor frames are kept. `room.json` says where "up" came from (`up_from`) and how far the floor was from the phone's guess (`floor_tilt_deg`).
4. `roompipe.build.build_room`: write the room folder: points (PLY and `bin`), anchors, every frame with its camera and per-pixel points, `room.json`.
5. Optional, `roompipe.place.place_photos`: each batch of photos goes through the model twice with different anchors; a photo is pinned only if the two answers agree.
6. `roompipe.session.RunLog`: `run.json` records the GPU, the pinned versions, seconds and peak GPU memory per step, and any failure. A failed step stops the later ones, and the record is still saved.

If the GPU runs out of memory, the build is retried with 40, then 30 frames (`session.build_with_fallback`).

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Run the model in Colab for the first draft | **Builder, 16 Nov** (design approach A) | No GPU on the laptop; wiring Django to a GPU host is after the draft |
| Apache weights only | **Builder** (project rule) | Commercial-friendly licence |
| Pin the weights revision and the MapAnything commit | Claude, 17 Nov | The weights were republished in January 2026; the draft's evidence has to be repeatable |
| Save every frame, its camera and per-pixel points, not only the thinned points | Claude, 17 Nov | Another way of placing photos can then be tried without running the model again |
| Files reach Colab through Google Drive | Claude, 17 Nov | A phone can upload a large video straight to Drive, and results survive a Colab disconnect |
| The code reaches Colab as a zip | Claude, 17 Nov | The repository is private, so Colab cannot fetch it |
| Photos are copied with no EXIF | Claude, 17 Nov | Their GPS position never leaves the copy step; the date and focal length are read first |
| A stand-in model can run the whole notebook | Claude, 17 Nov | The notebook could be tested end to end without a GPU. Everything it makes is labelled a made-up room |
| **The floor is the lowest flat layer, and the room is levelled by the floor's own plane; the first real room is corrected on the laptop, not rebuilt** | **Builder, 18 Nov** (option 1 of 3, on Claude's recommendation) | The first real run took the bed top for the floor: the old rule kept the fullest 1 cm slice, and the bed top beat the floor 3,471 points to 3,351. "Up" from the phone also leaned 1.9° toward the way it faced most, which spread the floor over several slices. The model's output was fine, so only the last step needed redoing. The other options were importing the room as it was (everything 0.66 m too low) or filming again (the old code would pick the bed again) |
| A layer counts if it is at least half as full as the fullest and twice a typical slice | Claude, 18 Nov | Walls alone make "typical" slices. On the first real room (counting each slice with its two neighbours) the floor reached 2.55 times a typical slice and the bed top 2.38 times: both stand out, and the lower one is taken |
| The floor's plane is found by RANSAC (300 tries, 2 cm), only among planes within 15° of the phone's up | Claude, 18 Nov | Walls cross the floor layer and pulled a plain fit off (a test showed it). The 15° limit means a wall or a ramp can never become the floor; real floors were 2° off |
| Re-levelling uses the smallest turn that levels the floor, on the room's own `points.ply`, into a new folder | Claude, 18 Nov | The smallest turn keeps the room's heading, so nothing else moves. The original zip stays as the record of the GPU run; `room.json` gets a `relevelled` record with the old values |

### Known gaps

- **First real run, 18 Nov 2026 (13:42 UTC), Colab T4:** 60 frames fit in one try (peak 10.9 of 15.6 GB); the model pass took 36 s and the build step 63 s. Several walls show as parallel lines about 10 cm apart, so some frames do not line up exactly. Neither of the two photos was placed: the anchors lined up only to within 1.16 m.
- Nothing corrects the model's scale. If its "metric" output is 5% off, so is the room.
- Portrait photos run with landscape frames are cropped by the model's image loader.

---

## Piece 7: Photos

**Status, 18 Nov 2026:** applied from `prebuilt/django/chunk5-parts` and `prebuilt/django/chunk5-rest/D2a-D3a` (step C1 of `docs/plans/2026-11-18-first-draft-finish.md`). D2 and D3 are the builder's answers of 17 Nov. The plan's other calls for chunk 5 (listed under "Decisions and why") have not been read out to the builder yet, and the walk-through is folded into the combined walk-through (step B6).

### What it does

Lets a person add photos to a place, see them in a grid, give each a caption and a date, and delete them. The app calls a photo with its caption and date a **memory**.

- Many photos are picked in one go. Captions are added afterwards, photo by photo.
- A photo file can only be fetched by its owner, logged in.

| Address | Page | View |
| --- | --- | --- |
| `/places/<slug>/memories/new/` | Add photos | `memory_create` |
| `/memories/<number>/edit/` | One photo, large, with its caption and date | `memory_edit` |
| `/memories/<number>/delete/` | Asks first, then deletes | `memory_delete` |
| `/memories/<number>/photo/` | The photo file itself | `memory_photo` |

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/photos.py` | `photo_taken_on`: reads the capture date from inside a photo |
| `rooms/validators.py` | `validate_photo`: size, and "is really a JPEG, PNG or WebP" (`PHOTO_FORMATS`) |
| `rooms/forms.py` | `MultipleFileInput`, `MultipleImageField`, `MemoryUploadForm` (adding) and `MemoryForm` (caption and date) |
| `rooms/access.py` | `get_own_memory(user, pk)` |
| `rooms/views.py` | `memory_create`, `memory_photo`, `memory_edit`, `memory_delete` |
| `rooms/models.py` | `Memory.photo_address()`: the address pages use to show a photo |
| `rooms/templates/rooms/` | `memory_upload.html`, `memory_form.html`, `memory_confirm_delete.html`, and the "Photos" section of `place_detail.html` |
| `config/settings.py` | `MAX_PHOTO_BYTES` (20 MB), `MAX_PHOTOS_PER_UPLOAD` (50) |
| `rooms/tests/` | `test_memories.py` (20 tests), `test_memory_pages.py` (21), `test_memory_upload.py` (23), `test_memory_files.py` (8) |

### How one request flows

Uploading three photos to "Dorm":

1. `POST /places/dorm/memories/new/`, a multipart request carrying three files under the one name `photos`.
2. `views.memory_create` → `@login_required` → `get_own_place`.
3. `MemoryUploadForm.is_valid()` → `MultipleImageField.clean`: at most 50 files; each file must be non-empty and pass `validate_photo`. Every failure is collected as "file name: reason". One bad file refuses the whole upload.
4. Inside one database transaction, for each file: `photo_taken_on(file)` reads its date, and a `Memory` row is created. `memory_photo_path` picks the stored name (a random one, under `media/places/<place id>/memories/`).
5. "3 photos added." and a redirect to the place's page.

Then the place's page lists the photos, and the browser asks for each image. Each `<img>` points at `/memories/<number>/photo/`. `views.memory_photo` → `@login_required` → `get_own_memory` (404 for anyone else) → the file is sent with `Cache-Control: private, max-age=3600`. A row whose file has gone from disk gives 404.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| D2 = a: many photos at once, captions afterwards | **Builder, 17 Nov** (Claude's recommendation) | It is the web version of picking from the gallery: people have dozens of photos of a room. One per form would be slow for thirty |
| D3 = a: a photo file only through a view that checks the owner | **Builder, 17 Nov** (Claude's recommendation) | Private by default. Open addresses would let anyone with a link see the photo, logged in or not. At deployment this becomes time-limited bucket links |
| JPEG, PNG and WebP only, 20 MB each | Claude, 16 Nov | They are what browsers show and Pillow reads. HEIC gets a plain message |
| A photo is judged by its content, not its name | Claude, 16 Nov | The name is whatever the sender says |
| At most 50 photos per upload; one bad file refuses the batch | Claude, 16 Nov | Simple to explain. Saving the good ones and skipping the bad is friendlier and is a later improvement |
| The date is read from inside the photo when it has one | Claude, 16 Nov | Saves typing; it can be edited afterwards |
| Each file is checked by `validate_photo`, not also by Django's `ImageField` | Claude, 16 Nov | Django's check would give a HEIC photo its generic "not a valid image" message before ours could say "HEIC is not supported yet" |
| Pages get a photo's address from `Memory.photo_address()` | Claude, 16 Nov | One line to change when photos move to a storage bucket |
| A photo's own page is its edit page | Claude, 16 Nov | Tapping a photo opens it large with its caption and date boxes; no separate view-only page |
| Location data inside photos is left alone for now | Claude, 16 Nov | It belongs with the security work before deployment |
| The grid shows full-size photos scaled down | Claude, 16 Nov | No thumbnail code yet; fine for tens of photos |

### Checked

- 195 tests pass (18 Nov), 72 of them for this piece.
- A real server (a scratch copy with its own database, 18 Nov): 14 of 14 HTTP checks passed. Three JPEGs uploaded in one request ("3 photos added.", "Photos (3)", the dated one shown as 9 May 2026); the owner gets the file as `image/jpeg` with `private, max-age=3600`; a logged-out visitor is sent to login; a second user gets 404 on the file and on the photo's page; `/media/` and a stored file's real `/media/...` path both give 404. The photos were small images made by Pillow, not phone photos, and nothing was looked at in a browser.

### How to change it

- **Change a limit:** `MAX_PHOTO_BYTES` and `MAX_PHOTOS_PER_UPLOAD` in `config/settings.py`. Messages and help text follow.
- **Accept another photo type:** `PHOTO_FORMATS` in `rooms/validators.py`, and the `accept` attribute on the upload field in `rooms/forms.py`. HEIC needs an extra library.
- **Change where photos are fetched from:** `Memory.photo_address()`.
- **Add a field to a memory:** the model, a migration, and `fields` in `MemoryForm`.

### Known gaps

- No thumbnails.
- Location data stays inside uploaded photos.
- No HEIC: an iPhone set to "High Efficiency" gets a message, not an upload.
- A double tap on the upload button can upload twice.
- If saving fails part-way through a batch, the rows are rolled back but files already written are left on disk.
- Every image request runs Python, which is fine at this size and slow at a large one.

---

## Piece 8: Bringing a built room into the app (`import_room`)

**Status, 18 Nov 2026:** built and tested (step C6 of the run sheet). Run on the made-up demo room from `python -m roompipe demo`; **not yet run on a real room.** Built without the builder present; the calls below are listed for them.

### What it does

Takes the room folder (or zip) that the Colab notebook made, checks it, attaches its points to a scan, and marks the scan ready, so the 3D viewer page can show it. For the first draft this is the only way a room reaches the app: the builder runs it by hand after downloading the zip.

```powershell
.venv\Scripts\python.exe manage.py import_room <scan number> <room folder or .zip> [--made-up]
```

The scan number is the "Id" column in the admin site's Scans list (`/admin/rooms/scan/`), added for this command.

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/management/commands/import_room.py` | The command: find the scan, check the room, store the file, save the facts, mark it ready |
| `rooms/roomfolder.py` | Finds the room in a folder or zip; reads `room.json` and `run.json`; checks `points.ply` byte by byte against the layout the AI code writes; decides "made up" and "allowed model". Standard library only |
| `rooms/models.py` | `Scan.room_info` (new, migration `0004_scan_room_info`); the points file now ends `-points.ply` |
| `rooms/admin.py` | The Scans list shows each scan's number ("Id") |
| `rooms/tests/test_import_room.py` | 22 tests (21 for the command, 1 for the admin column) |

### How one import flows

1. `import_room 4 Downloads\room-2026-11-18.zip` → `Scan.objects.get(pk=4)`, or "No scan number 4".
2. `open_room`: a folder, a folder holding one room folder, or a zip whose room is at the top or inside one folder. Nothing is unpacked: only `room.json`, `run.json` and `points.ply` are read, by name.
3. `check_room`: `run.json` if present; then `room.json` must exist (if not, the run failed, and `run.json`'s "stopped because" is quoted), be version 1, and agree with `points.ply` on the point count. The PLY's header must be exactly Memory Room's layout and its length exactly header + 15 bytes per point.
4. Which model made it: the stand-in model's rooms need `--made-up`; a real room must name `facebook/map-anything-apache` (the project's licence rule); a room that names no model is refused.
5. `points.ply` is copied into `media/places/<id>/scans/<random>-points.ply`. `room_info` gets the point count, the box in metres, up consistency, frames used, model, weights revision, precision, GPU, run name, `made_up`, and when it was imported. Status becomes "ready". An older points file on the same scan is deleted.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| A built room reaches the app through a management command run on the downloaded folder | **Builder, 17 Nov** (Claude's recommendation) | The AI runs in Colab for the draft; a command is the smallest honest bridge. By 8 Dec a view starts the GPU job and its result goes through the same checks |
| The viewer reads PLY, so the stored file ends `.ply` | **Builder, 17 Nov** | A standard format that 3D tools open too |
| The room's facts go in one JSON field, `Scan.room_info` | Claude, 18 Nov | Design §6 said `n_points` and `room_box` would arrive with the viewer; one field holds those and the run's facts (model, GPU, precision) without a migration for each. Searching by them is not needed |
| A stand-in room is refused unless `--made-up` is given, and is then labelled made up everywhere | Claude, 18 Nov (run sheet) | A fake room must never be shown as a result; the class forbids fabricated outcomes |
| `--made-up` on a real room is refused | Claude, 18 Nov | So the label is never wrong in either direction |
| A room from any weights other than `facebook/map-anything-apache` is refused | Claude, 18 Nov | The project's licence rule, checked where the result enters the app as well as where the model loads |
| The PLY is checked byte by byte; the count must match `room.json` | Claude, 18 Nov | A file the viewer would misread fails here, with a reason, instead of showing a broken room |

### Checked

- 21 tests (the whole suite: 216, 18 Nov). A good room from a folder, a zip, a zip with one folder inside, a folder holding one room folder; importing again replaces the file; and each refusal: unknown scan, nothing at the path, a failed run (its reason quoted), another version, no PLY, not a PLY, another layout, cut short, counts that disagree, no model named, the non-commercial weights, a made-up room without the flag (seen in `run.json` or in `room.json`), and the flag on a real room.
- On a scratch copy of the app, the demo room from `python -m roompipe demo` (written by the AI code's own PLY writer), zipped the way the notebook zips: refused without `--made-up`; with it, "Scan 1 is ready: 98,329 points, in a box 4.17 x 3.24 m across and 2.50 m high"; the stored file is byte-for-byte the room's `points.ply`; importing the folder again left one points file on disk.

### Known gaps

- Run by hand; nothing in the app starts it.
- Photo placements in the room (`placements.json`) are not imported: the command cannot tell which `Memory` each photo is. That waits for placement inside the app.
- The box is the room's extent along the room's own axes; until walls are lined up with the axes it is larger than the room.

---

## Piece 9: The 3D room page

**Replaced on 18 Nov by piece 10** (the place page is now the room; `scan_room.html` and `roomviewer.js` are gone). Kept here as the record of how the first viewer worked.

**Status, 18 Nov 2026:** built and tested (step C7 of the run sheet); seen in a real browser with the made-up demo room. **Not yet shown a real room, and not opened on a phone.** Built without the builder present; the calls below are listed for them.

### What it does

Shows the room built from one scan as coloured dots you can turn and zoom, with each placed photo as a dot on a stalk (orange: placed by the AI; blue: by hand). Tapping a dot shows that photo below the room, with a link to its page. Two views: standing inside, and from above with the ceiling cut away. A room made by the stand-in model carries a "MADE-UP ROOM" notice.

| Address | What | View |
| --- | --- | --- |
| `/scans/<number>/room/` | The page | `scan_room` |
| `/scans/<number>/points.ply` | The room's points file | `scan_points` |

On a place's page, each ready scan has a "View the room in 3D" link. One page per scan, so each version of a place (core feature 3) will have its own.

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/views.py` | `scan_room`, `scan_points`, and `_get_own_built_scan` (owner check, then "is it built?") |
| `rooms/templates/rooms/scan_room.html` | The page: import map, notice, the room, two view buttons, the chosen photo, and a short script that loads the points and starts the viewer |
| `static/viewer/roomviewer.js`, `loaders.js` | The viewer and the PLY reader, copied unchanged from `prebuilt/viewer/` |
| `static/viewer/vendor/` | three.js 0.170.0 and its `OrbitControls`, unchanged, with their MIT licence |
| `templates/base.html` | A new `{% block head %}` for the page's import map |
| `rooms/templates/rooms/place_detail.html` | The "View the room in 3D" link |
| `static/css/site.css` | One block at the end, and a `--warn-bg` colour for the notice |
| `rooms/tests/test_scan_room.py` | 12 tests |

### How one request flows

1. `GET /scans/4/room/` → `views.scan_room` → `@login_required` → `get_own_scan` (404 for anyone else) → 404 too if the scan is not "ready" or has no points file.
2. The view lists the scan's pins (photo caption, x, y, z, who placed it, the photo's owner-checked address, its page) and hands them, the box from `room_info` and the points file's address to the template, which writes them out with `json_script`. A caption is data, never code.
3. The browser loads three.js through the import map, then fetches `/scans/4/points.ply` → `views.scan_points` → the same two checks → the file, `application/octet-stream`, `Cache-Control: private, max-age=3600`.
4. `loaders.js` reads the PLY (only Memory Room's layout); `roomviewer.js` draws it. Tapping a dot fetches its photo through `/memories/<number>/photo/`, which checks the owner again.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Coloured points in a three.js page inside the app | **Builder, 16 Nov** (approved design §7) | The design's first-draft viewer |
| The page reads PLY | **Builder, 17 Nov** | — |
| The page lives at `/scans/<number>/room/`, one per scan | Claude, 17 Nov (run sheet) | A room belongs to a scan, so versions each get a page. `prebuilt/viewer/README.md` had sketched `/places/<slug>/room/` |
| The points file goes through an owner check, like photos | Claude, 17 Nov (run sheet; follows D3 a) | `media/` is not public; a room shows the inside of someone's home |
| An unbuilt scan's page is a 404, not a "not ready yet" page | Claude, 18 Nov | The link only appears once a scan is ready; a friendlier page can come with the GPU job |
| three.js is a copy in `static/`, not from a CDN | Claude, 16 Nov (viewer kit) | Works with no internet, for the class demo |
| Dots 3 cm wide; two views; colours drawn as stored | Claude, 16 Nov (viewer kit) | See `prebuilt/viewer/README.md`, "Calls made here" |
| No hand placement on this page yet | Claude, 18 Nov | Saving a hand-placed pin needs a POST view and a choice of photo; the run sheet counts it as an extra. The viewer already supports it (`startPlacing`) |
| A tapped dot shows the photo, its caption, who placed it, and a link | Claude, 18 Nov | The smallest useful answer to "what was taken here?" |

### Checked

- 12 tests (the whole suite: 228, 18 Nov): login needed for both addresses; another user gets 404 on both; an unbuilt scan gives 404; the page carries the viewer, the points address, the box and the pins; pins of another scan are left out; a caption with `</script>` cannot break out of the data; the made-up notice shows only for a made-up room; the file comes back as `application/octet-stream`, private, byte for byte; a missing file gives 404; the place page links only ready scans.
- In Chromium (Playwright), on a scratch copy of the app with the demo room imported (`--made-up`) and three photos pinned by hand from the demo's `placements.json`: 98,329 points and 3 pins drawn; the notice shown; tapping a pin showed its photo (loaded through the owner check), caption and link; "Look from above" works; at 390 px wide nothing scrolls sideways. The only console error was `/favicon.ico` (404), which every page of the site has.

### Known gaps

- Not yet shown a real room, which will be noisier than the demo. Not tried on a phone (touch, and speed with real point counts).
- No hand placement, no pin list, no way to move a pin yet (the JSON API, planned for 29 Nov).
- The whole points file is downloaded each visit (cached for an hour); a large room may be slow on a phone connection.
- The site has no favicon, so every page logs one 404.

---

## Piece 10: The Dollhouse look (18 Nov 2026)

**Built 18 Nov, by Claude, from the builder's decisions; not committed; walk-through owed.** Design: `docs/design/2026-11-18-dollhouse-site.md` (with its bug review). Plan: `docs/plans/2026-11-18-dollhouse-site.md`. Mockup the builder approved: `docs/design/mockups/a2-dollhouse-app.html`.

### What it does

The whole site in one look: a slate field (the colour of the builder's bedspread) with the room on it, pink (the room's own light) for photos and the main action, Gloock for names, Onest for text.

| Page | Address | What it is now |
| --- | --- | --- |
| Front page (logged out) | `/` | The public landing room: its dots gather into the room, which turns slowly beside "Keep the room." Without a landing room, the words alone |
| Your places | `/places/` | Each place with a built room is a small turning model of it (at most three); the others, and "Film a new place", are dashed plots |
| A place with a built room | `/places/<slug>/` | The room, full screen, from above with the walls cut low. Placed photos are pink dots on stems; a strip holds every photo, unplaced ones dashed. Tap a photo: the camera flies to where it was taken. A ⋯ menu: add photos, add a room video, the videos, rename, delete |
| A photo, opened | `/places/<slug>/?photo=<id>` | With a camera direction: the photo lined up in the room. Without one (hand-placed): the camera looks down at the spot and the photo shows as a card. Back closes it |
| Placing a photo | same page | From straight above: "Tap where you stood". The tap is saved through `POST /scans/<n>/pins/` and the dot drops in |
| A place with no room yet | `/places/<slug>/` | What's missing, by the newest video's state (uploaded, building, failed), a dashed footprint, the photos so far |
| Every form | as before | A narrow column on the field, the room faint and blurred behind it |
| One built room | `/scans/<n>/room/` | The same room page, for that scan |

### Where the code is

| File | What it is |
| --- | --- |
| `rooms/models.py`, `migrations/0005_pin_camera.py` | `Pin.camera`: which way the camera faced and how wide it saw (nullable; checked in `Pin.clean()`) |
| `rooms/pins.py` | `pin_save`: place or move a photo by hand (JSON) |
| `rooms/room_page.py` | `room_context` (everything the room page needs, one dict for `json_script`) and `points_url` |
| `rooms/landing.py`, `management/commands/landing_room.py` | The public landing room: a thinned copy of one built room, no photos |
| `rooms/templatetags/backdrop.py` | `{% backdrop_url place %}`: which room to draw faintly behind a page |
| `rooms/access.py` | `get_own_built_scan` moved here from `views.py`, shared by the room page and `pin_save` |
| `rooms/management/commands/import_room.py` | Refuses to replace a room whose scan has pins, unless `--drop-pins` |
| `static/viewer/room3d.js` | The new viewer (replaces `roomviewer.js`): draws only while something moves, flights that a newer one can replace, the scan's frame in and out |
| `static/viewer/roomgeom.js` | Plain geometry, tested in Node: `wallAngle`, `turnXY`/`unturnXY`, `footprint` |
| `static/site/*.js` | One script per page: `landing`, `places`, `room`, `backdrop`; shared camera positions in `views.js` |
| `static/css/site.css`, `templates/base.html`, all templates | The look |
| `static/favicon.svg` | A pink dot on slate |

### How placing a photo flows

1. The person taps a dashed photo in the strip. `room.js` flies the camera overhead and waits for a tap (a press that moves less than 6 px).
2. `room3d.floorAt` turns the tap into a point on the floor **in the scan's own frame**: the room is drawn turned so its walls line up with the screen, and the turn is undone here (S1). `onFloor` refuses a spot outside the room's footprint, such as the empty corner of an L-shaped room (S5).
3. `fetch POST /scans/<n>/pins/` with `memory`, `x`, `y` and the CSRF token → `pins.pin_save` → `@login_required`, POST only → `get_own_built_scan` and `get_own_memory` (404 for anyone else's) → same place? numbers? inside the box? → `update_or_create` the pin at 1.4 m, `placed_by="user"`, `camera=None` → JSON.
4. The page drops the dot in at the answer's spot and flies back to the room.

### Decisions and why

| Decision | Who, when | Why |
| --- | --- | --- |
| Direction A, "Dollhouse", from three mockups | **Builder, 18 Nov** | One continuous space; every move is a camera move |
| Django's pages stay; the place page becomes the room; page-to-page moves use view transitions | **Builder, 18 Nov** | Low risk on the day the draft is due; keeps the tests |
| The front page shows the builder's own room, thinned, with no photos | **Builder, 18 Nov** | The strongest first look; photos stay owner-only (D3) |
| `Pin.camera` added (changes the §6 data model) | **Builder, 18 Nov** | Lined-up photos for placements that know their camera; no pins existed yet |
| Photos placed by hand tonight; no video frames as photos | **Builder, 18 Nov** | Hand placement was decided on 17 Nov |
| The design and its fixes S1–S8, M1–M12 | **Builder, 18 Nov** (approved) | Found in a bug review before building |
| `import_room` refuses a scan with pins unless `--drop-pins`; taps outside the room's footprint are refused | Claude, 18 Nov (listed for the builder) | A rebuilt room has its own frame; an L-shaped room's box covers empty floor |
| Logged out, the header is the wordmark only | Claude, 18 Nov | The front page's own buttons would otherwise be said twice |
| Dots on thin stems down to the floor | Claude, 18 Nov | A dot floats at camera height; the stem shows where it stands (the old viewer had them for the same reason) |
| The footprint uses every point under 2 m, not only the floor | Claude, 18 Nov | The floor under the builder's bed was never filmed |
| Browser checks ran on a copy of the database and media | Claude, 18 Nov | Test photos and pins never touched the builder's data |

### Checked

- Django: 276 tests (18 Nov), of which new: `Pin.camera` rules (3), `pin_save` (12), room page data, `?photo=`, scan states, delete wording (13), `import_room` with pins (2), landing room (8), places page (3). Older tests that expected the old words were changed on purpose, each marked "18 Nov" in the test.
- Node: 5 geometry tests (`node --test "static/viewer/tests/*.test.mjs"`). On the real room, `wallAngle` gives 74.75° (the Python check gave 74.5°) in 185 ms.
- Chromium, on a copy of the builder's data, at 1280×800 and 390×844: every page; 7 photos uploaded through the page; a photo with a real MapAnything camera pose opens lined up; Back closes a photo; a photo placed by tapping a paper sheet comes back on that sheet after a reload (S1); taps in the L's empty corner and off the room are refused (S5); two fast taps end on the second photo (M1); Escape; Tab reaches nothing hidden (M6); a 50-photo strip starts at the left (M5); reduced motion gives cuts (M9); turning a phone re-fits the room (M12); places → room continues the camera move. No console errors except one: Chrome logs "Transition was aborted" after a file upload's redirect (the cross-fade is skipped; nothing breaks).

### Known gaps

- A pin can be moved but not removed.
- A browser can keep an old copy of the page scripts after an update (seen while checking); deployment will need hashed file names (Django's `ManifestStaticFilesStorage`).
- Placing a photo needs a pointer: there is no keyboard way to choose a spot.
- The places page draws at most three rooms; it downloads each room's whole points file.
- Fonts come from Google Fonts; with no internet the page falls back to Georgia and the system sans.

## Code review, 18 Nov 2026

The builder ran `/code-review` on PR #1 (everything since `first-push`) at about 00:45 on 18 Nov. It reported 15 findings; Claude checked each against the code and all 15 held. 12 were fixed, each with a test that was seen to fail first; 3 were deferred. Afterwards: 240 Django tests and 96 AI tests pass, the code zip was re-packed, and the notebook rehearsal passed.

| # | Finding | Piece | What was done | Test |
| --- | --- | --- | --- | --- |
| 1 | `rehearse_notebook.py` emptied whatever folder it was given | 6 | It refuses a folder holding anything but an earlier rehearsal | `ai/tests/test_rehearse.py` (3) |
| 2 | A photo's stored ending came from the browser's file name, and its type from that ending: a JPEG named `.html` was served as a web page | 7 | The ending now comes from the format found inside the photo, and the photo view serves only image types (anything else as a download) | `test_stored_ending_follows_the_content`, `test_png_named_jpg_is_stored_as_png`, `test_a_file_with_another_ending_is_never_served_as_a_page` |
| 3 | The points file was cached for an hour at a fixed address, so a re-imported room could show the old (perhaps made-up) points | 9 | The address carries the file's random name, which changes with every import | `test_points_address_changes_when_the_room_is_replaced` |
| 4 | The import ignored a `run.json` that says the run did not finish, and did not check that `run.json` and `room.json` name the same model | 8 | Both are refused, with the reason | `test_failed_run_beside_an_old_room_refused`, `test_files_from_different_runs_refused` |
| 5 | A failed model pass during placement was recorded as "ask the person" for every photo | 6 | The model call is outside the "could not fit" handler; a failure stops placement and is written in `run.json` | `test_a_model_failure_is_not_recorded_as_photos_to_ask_about` |
| 6 | A rerun could leave an earlier room beside a new, failed `run.json`, and the Drive save merged folders of the same name | 6 | A run empties its room folder at the start; the save uses a new name when one exists | Rehearsal (passed); #4 guards the import |
| 7 | A photo dated in the future (camera clock ahead) was stored, and its caption then could not be saved | 7 | A future date from inside a photo is not kept | `test_future_date_inside_a_photo_is_not_kept` |
| 8 | `FIRST_DRAFT.md` read as if the first real run had happened | — | Reworded: "not yet run; planned for 18 Nov" | Read by hand |
| 9 | The place page did not label a made-up room | 9 | "MADE-UP ROOM (not a reconstruction)" beside that scan | `test_place_page_labels_a_made_up_room` |
| 10 | A damaged zip crashed the import with a traceback and could leave a partial file in `media/` | 8 | The points are copied to a temporary file first; a damaged zip is refused with a message, and nothing reaches `media/` | `test_damaged_zip_refused`, `test_damaged_zip_found_while_copying_leaves_no_file` |
| 11 | Files are deleted when their rows are, inside the database transaction; a rollback brings the rows back without the files | 7 | **Deferred.** Rare on SQLite with one user; the fix (`transaction.on_commit`) changes several existing tests | — |
| 12 | The "inside the room" check looked at the first try, but the pin goes at the middle of the two | 6 | It checks the spot that is pinned | `test_the_pinned_spot_itself_must_be_inside_the_room` |
| 13 | Tapping a dot did not enlarge it | 9 | It does (`viewer.selectPin`) | Seen in Chromium |
| 14 | The page's import map uses `{% static %}` on a folder, which fails with the static storage used at deployment | 9 | **Deferred** to deployment; listed below | — |
| 15 | `points.bin` is still written though the viewer reads PLY; `parseBin` and `Place.newest_ready_scan` are unused | 6, 9 | **Deferred**: a clean-up, nothing breaks | — |

---

## Before deployment

Things that are right for a laptop and wrong for a public site. Nothing here is a fault today.

- Cookies are not marked secure-only, and plain HTTP is not redirected to HTTPS. `manage.py check --deploy` lists four warnings, all of this kind.
- With debug off, Django's development server stops serving the stylesheet. A real host serves static files itself.
- SQLite and local disk are to be replaced (Postgres and a file bucket in the technical design).
- The 3D page's import map points `{% static %}` at a folder (`viewer/vendor/`). With a hashed static storage (`ManifestStaticFilesStorage`, WhiteNoise) that fails and every 3D page gives 500. Point it at the one `OrbitControls.js` file, or build the folder address from `STATIC_URL` (code review, 18 Nov, #14).
- Files are deleted inside the delete's transaction (`rooms/signals.py`); move to `transaction.on_commit` before a real database (code review, 18 Nov, #11).
