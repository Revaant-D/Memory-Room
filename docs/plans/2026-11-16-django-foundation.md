# Django Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans to run **one chunk per session**, in this session, with the builder present. Use superpowers:test-driven-development inside each task. Steps use checkbox (`- [ ]`) syntax; tick them as you go. `CLAUDE.md` overrides any skill: read "How the builder wants to work" there before anything else.

**Goal:** A working Django app where a person signs up, creates a place, uploads a room video and photos, captions the photos, and sees only their own places.

**Architecture:** One Django project (`config`) with two apps: `accounts` (the user, sign-up, login) and `rooms` (places, scans, memories, pins). Plain function views and Django templates, SQLite, uploaded files on local disk under `media/`. Every page that touches a place goes through one small file of owner checks, so "each user sees only their own places" is enforced in one spot.

**Tech stack:** Python 3.14, Django 5.2 (long-term support), Pillow, SQLite, Django's built-in test runner. No JavaScript and no CSS framework in this plan.

**Spec:** `docs/design/2026-11-16-first-draft.md`. §6 is the approved data model; §7 row "Django foundation (40)" is what this plan delivers. Class requirements: `docs/reference/assignment.md`.

## How to use this plan across sessions

This plan is cut into six chunks. Each chunk is one sitting with one Claude session and ends with working, tested software.

| Chunk | What exists when it is done | Rough time | Status |
| --- | --- | --- | --- |
| 1. Skeleton and accounts | The project runs; sign-up, login, logout work | 60–75 min | Built, recorded and committed (`4ed4bda`) 16 Nov. Still to do: the builder's walk-through |
| 2. The four models | Place, Scan, Memory, Pin with their rules, visible in the admin | 60 min | Applied from `prebuilt/` and recorded 17 Nov; 78 tests at that point. Not committed. Still to do: read out the calls, the walk-through |
| 3. Places pages | Create, list, open, rename, delete a place; other users get a 404 | 60 min | Applied from `prebuilt/` and recorded 17 Nov; 99 tests at that point. Not committed. Still to do: read out the calls, the walk-through |
| 4. Room video upload | Upload and delete a room video on a place | 45 min | Applied from `prebuilt/` and recorded 17 Nov; 123 tests. Not committed. Still to do: read out the calls, the walk-through (it uploads the real room video) |
| 5. Photos | Upload many photos, caption them, delete them; photos are private | 75 min | Applied from `prebuilt/` (D2 a, D3 a) and recorded 18 Nov; 195 tests. Not committed. Still to do: read out the calls, the walk-through (combined walk-through, run sheet step B6) |
| 6. Runs from a fresh clone | README; a clean copy installs, passes its tests and starts | 30 min | ☐ |

Times are Claude's estimates and include the walk-through.

**Order.** 1 → 2 → 3 are strict. 4 and 5 both need 3 and can be done in either order. 6 is last.

**If time runs short.** Chunks 1, 2, 3 and 6 alone meet every line of the first-draft "Functional Django foundation" requirement (two models with a relationship, views, templates, a form, one database-backed workflow). Chunks 4 and 5 are what make it this product.

**Every session follows the same five steps** (the first four are the builder's loop in `CLAUDE.md`):

1. **Orient.** Read `CLAUDE.md`, §6 of the spec, this plan's header and the chunk you are about to do. From chunk 2 on, run the tests first (`.venv\Scripts\python.exe manage.py test`) and confirm they pass before changing anything. If they fail, stop and tell the builder.
2. **Decide.** Each chunk opens with a "Decide" block. Put the *builder's decisions* to the builder in plain words with the recommendation, and wait for the answer. Read out *Claude's calls* so the builder can overrule any of them. The tasks are written for the recommended options; each decision says what changes if the builder picks otherwise.
3. **Build.** Do the tasks in order. Write the tests first, watch them fail, write the code, watch them pass.
4. **Walk through.** Do the chunk's walk-through with the builder: trace the named action through the code, and have the builder run it themselves.
5. **Record.** Add the piece to `docs/system-map.md` as the chunk says. Tick the chunk in the table above. Update "Where things stand" in `CLAUDE.md`.

**Test counts.** Each task states how many tests should pass at its end, assuming the recommended options and no extra tests. Treat the number as a guide: if you add a test or the builder picks another option, it moves, and you say so. What must hold is that every listed test exists and passes.

**Talking to the builder.** The builder is one student who knows Django from class and wants to be able to explain every piece. Use plain words. When you make a call the plan did not list, say so and record it.

## Global constraints

- **Commits:** commit only when the builder asks (`CLAUDE.md`). At the start of a session, ask once whether you may commit at each task's commit point. Never push.
- **What goes into git:** add files by path. The builder made the repository themselves on 16 Nov, on branch `master`, and committed `docs/` and `.idea/`; keep that branch name and leave those tracked. `CLAUDE.md` is never committed (the builder's rule; see Rules in `CLAUDE.md` for the check to run before each commit). Commit messages carry no co-author line and no mention of the tool that wrote the code; the author is the builder. Whether `docs/` is *pushed* is still the builder's open question. Never add `.env` files, keys, `media/`, `db.sqlite3`, `.secret_key` or model weights.
- **Forms are drawn one way:** inside each `<form>`, `{% include "includes/form_fields.html" %}` draws the fields. Do not hand-write field markup per page.
- **Real results only:** never write that a test passed or a page works without having run it in this session.
- **Storage:** SQLite and local disk only.
- **Python:** every command uses the project's own interpreter, `.venv\Scripts\python.exe`. Do not rely on `python` on the PATH; this machine has four of them. Do not activate the environment (PowerShell may block the activate script); call the interpreter by path.
- **Shell:** PowerShell on Windows 11. Run commands from `C:\Users\revaa\AI Projects\memory-room`.
- **Versions:** Django `>=5.2,<5.3`. Latest Pillow (13.0.0 on 16 Nov 2026). If an installed library behaves differently from what this plan says, trust the library's own documentation and note the difference in the system map.
- **User model:** never import `django.contrib.auth.models.User` directly. Use `settings.AUTH_USER_MODEL` in models and `get_user_model()` elsewhere.
- **Owner checks:** every view that loads a Place, Scan or Memory gets it through `rooms/access.py`. Another user's object is a 404, never a 403.
- **Forms:** every `<form method="post">` has `{% csrf_token %}`; every form with a file input has `enctype="multipart/form-data"`.
- **Out of scope for this plan:** the 3D viewer, attaching a points file to a scan, creating pins from a page, any JSON API, search, deployment, the GitHub push, the scope page and roadmap. They get their own decisions and plans.

## Review focus

Inputs the spec does not mention that are likely to reach this app. Each has a test in the task that owns the code.

1. **A place named "New".** Its address would collide with the "create a place" page. Expected: it gets a different address and opens normally. (Task 3)
2. **A place name with no letters or digits**, such as emoji or a non-Latin script. Expected: it still gets a working address. (Task 3)
3. **A photo or video with an awkward file name**: spaces, emoji, slashes, 200 characters. Expected: stored under a generated name; the original name never reaches the disk. (Task 4)
4. **A photo with no date inside it, or a garbled one.** Expected: it uploads; the date is left empty. (Task 10)
5. **A photo row whose file has gone from disk** (the `media/` folder was cleared). Expected: the place page still loads; that photo's address gives a 404, not a crash. (Task 11)

Also covered: an iPhone HEIC photo gets a clear message (Task 10); a pin with coordinates that are not real numbers is refused (Task 5); text typed into a name or caption is shown as text, never run as HTML (Tasks 6 and 12).

## File map

```
memory-room/
├─ manage.py
├─ requirements.txt
├─ .gitignore
├─ README.md                       chunk 6
├─ config/
│  ├─ settings.py                  all settings
│  ├─ secret.py                    finds or creates the secret key
│  ├─ urls.py                      sends addresses to the two apps
│  └─ tests.py                     tests for secret.py
├─ templates/base.html             page frame: header, messages, content
├─ static/css/site.css             the one stylesheet
├─ accounts/
│  ├─ models.py                    User
│  ├─ forms.py                     SignupForm
│  ├─ views.py                     signup
│  ├─ urls.py                      /accounts/signup, login, logout
│  ├─ admin.py
│  ├─ templates/registration/      login.html, signup.html
│  └─ tests/test_accounts.py
└─ rooms/
   ├─ models.py                    Place, Scan, Memory, Pin
   ├─ slugs.py                     makes a place's address word
   ├─ signals.py                   removes files when rows are deleted
   ├─ access.py                    the owner checks
   ├─ validators.py                video and photo checks
   ├─ photos.py                    reads the date inside a photo
   ├─ forms.py                     PlaceForm, ScanForm, MemoryUploadForm, MemoryForm
   ├─ views.py                     one function per page
   ├─ urls.py
   ├─ admin.py
   ├─ templates/rooms/             one template per page
   └─ tests/                       utils.py, test_models.py, test_places.py,
                                   test_scans.py, test_memories.py
```

Git-ignored and created at run time: `.venv/`, `db.sqlite3`, `media/`, `.secret_key`.

---

# Chunk 1: Skeleton and accounts

**Ends with:** the dev server runs; a person can sign up, log out and log in.

## Decide

**Decided 16 Nov 2026: the builder chose b.** Do not ask again.

**Builder's decision D1: which user model.** This is the one choice in the whole plan that is hard to change later, because it must be made before the first database migration.

| | Option | Trade-off |
| --- | --- | --- |
| a | Django's stock `User`, used as it comes | Fewest parts. If the user ever needs an extra field (a display name, email login), Django makes the swap painful once real accounts exist |
| **b (recommended)** | Our own `User` class that is identical to Django's (three lines in `accounts/models.py`, one setting) | Behaves exactly the same today. Leaves the door open. Django's own documentation recommends this for every new project |

Logging in with an email address is not offered for the first draft; if the builder wants it, stop and re-plan this chunk. The spec's §6 says "Django's built-in user"; option b still is that user, kept in our own file. **If the builder picks a:** skip Task 2 step 3 and leave `AUTH_USER_MODEL` out of the settings. Nothing else changes.

**Claude's calls** (read them out):
- Django 5.2, the long-term-support line (supported to April 2028), not 6.1. The technical design names Django 5 and most teaching material matches it.
- Two apps, `accounts` and `rooms`, so sign-up code and room code stay apart. The spec named only `rooms`.
- Sign-up asks for a username and a password, nothing else. No email is collected, so there is no password reset yet.
- The secret key is never in git: it comes from the `DJANGO_SECRET_KEY` environment variable, or from a git-ignored `.secret_key` file that the app creates on first run. A fresh clone runs with no setup.
- Function views, not class-based views: every step of a request is visible in one function, which suits the walk-throughs.
- Django's built-in test runner, not pytest: nothing extra to install.
- One hand-written stylesheet, phone-first, no framework.
- Logging out is a button (a POST), as Django 5 requires.
- Time zone `America/Chicago`.

## Task 1: Project skeleton

**Files:**
- Create: `.venv/`, `manage.py`, `config/` (via `startproject`), `accounts/`, `rooms/` (via `startapp`), `config/secret.py`, `config/tests.py`, `templates/base.html`, `static/css/site.css`, `rooms/templates/rooms/home.html`, `rooms/urls.py`, `.gitignore`, `requirements.txt`
- Modify: `config/settings.py`, `config/urls.py`, `rooms/views.py`
- Delete: `accounts/tests.py`, `rooms/tests.py` (replaced by `tests/` packages, each with an empty `__init__.py`)

**Interfaces:**
- Produces: `config.secret.load_secret_key(base_dir: Path) -> str`; URL name `home` at `/`; template `base.html` with blocks `title` and `content`; settings `MEDIA_ROOT`, `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "home"`, `LOGOUT_REDIRECT_URL = "home"`.

- [x] **Step 1: Create the environment and the project**

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install "Django>=5.2,<5.3" Pillow
.venv\Scripts\python.exe -m django startproject config .
.venv\Scripts\python.exe manage.py startapp accounts
.venv\Scripts\python.exe manage.py startapp rooms
.venv\Scripts\python.exe -m pip freeze > requirements.txt
git init -b main
```

Expected: `manage.py` and `config/settings.py` exist. Do **not** run `migrate` yet; the user model in Task 2 must exist first. Check that `requirements.txt` is plain UTF-8 text (PowerShell's `>` can write UTF-16; if it did, rewrite the file with the Write tool).

- [x] **Step 2: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
db.sqlite3
media/
staticfiles/
.secret_key
.env
.env.*
!.env.example
.idea/
*.bin
*.safetensors
*.pt
*.pth
*.ckpt
```

- [x] **Step 3: Write the failing tests** in `config/tests.py` and `rooms/tests/test_home.py`

```python
# config/tests.py  (SimpleTestCase; uses a temporary directory, no database)
test_env_var_wins            # DJANGO_SECRET_KEY="from-env" -> returns "from-env", writes no file
test_creates_key_file        # no env var, empty dir -> returns a key of 50+ chars and .secret_key now holds it
test_reuses_key_file         # called twice on the same dir -> same key both times

# rooms/tests/test_home.py
test_home_shows_landing      # GET "/" -> 200, contains "Memory Room", "Sign up" and "Log in"
```

- [x] **Step 4: Run them and see them fail**

Run: `.venv\Scripts\python.exe manage.py test`
Expected: errors, because `config.secret` does not exist and `/` has no page.

- [x] **Step 5: Implement**

- `config/secret.py`: `load_secret_key(base_dir: Path) -> str`. Order: the `DJANGO_SECRET_KEY` environment variable; else the text of `base_dir / ".secret_key"`; else make one with `django.core.management.utils.get_random_secret_key()`, write it to that file and return it.
- `config/settings.py`:
  - `SECRET_KEY = load_secret_key(BASE_DIR)` (delete the generated key line).
  - `DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"`
  - add `"accounts"` and `"rooms"` to `INSTALLED_APPS`
  - `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]`
  - `STATICFILES_DIRS = [BASE_DIR / "static"]`
  - `MEDIA_ROOT = BASE_DIR / "media"`
  - `TIME_ZONE = "America/Chicago"`
  - `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "home"`, `LOGOUT_REDIRECT_URL = "home"`
- `config/urls.py`: `admin/`, `accounts/` → `accounts.urls` (added in Task 2), `""` → `rooms.urls`.
- `rooms/urls.py`: `""` → `views.home`, name `home`.
- `rooms/views.py`: `home(request)` renders `rooms/home.html`.
- `templates/base.html`: header with "Memory Room" linking to `home`; a region that loops over Django `messages`; `{% block content %}`. The right side of the header is filled in Task 2.
- `rooms/templates/rooms/home.html`: one sentence saying what the product is ("Film a room once. It becomes a 3D room you can turn, with your photos pinned where you took them.") and links to sign up and log in. The 3D part is not built: the page must not say it works.
- `static/css/site.css`: readable on a phone, content column at most 720px wide, system font. Keep it under about 150 lines.

- [x] **Step 6: Run the tests and see them pass**

Run: `.venv\Scripts\python.exe manage.py test`
Expected: 4 tests, OK. (The `Sign up` and `Log in` links can be plain `/accounts/...` paths until Task 2 names them.)

- [ ] **Step 7: Commit point**

```powershell
git add .gitignore requirements.txt manage.py config accounts rooms templates static
git status   # confirm: no .venv, no .secret_key, no db.sqlite3, no docs, no CLAUDE.md
git commit -m "Project skeleton: config project, accounts and rooms apps, home page"
```

## Task 2: Sign-up, login, logout

**Files:**
- Create: `accounts/forms.py`, `accounts/urls.py`, `accounts/templates/registration/login.html`, `accounts/templates/registration/signup.html`, `accounts/tests/test_accounts.py`, `accounts/migrations/0001_initial.py` (generated)
- Modify: `accounts/models.py`, `accounts/admin.py`, `accounts/views.py`, `config/settings.py`, `templates/base.html`

**Interfaces:**
- Produces: `accounts.User` (same fields as Django's user); URL names `signup` (`/accounts/signup/`), `login` (`/accounts/login/`), `logout` (`/accounts/logout/`); `accounts.forms.SignupForm`.

- [x] **Step 1: Write the failing tests** in `accounts/tests/test_accounts.py`

Use the password `pass-12345-word` throughout.

```python
test_user_model_is_ours          # get_user_model()._meta.label == "accounts.User"   (skip if D1 = a)
test_signup_page_loads           # GET /accounts/signup/ -> 200
test_signup_creates_user_and_logs_in
    # POST username="ana", password1, password2 -> 302 to "/";
    # a user "ana" exists; "_auth_user_id" in self.client.session
test_signup_password_mismatch    # -> 200, no user created, the form has an error on password2
test_signup_duplicate_username   # "ana" exists -> 200, still exactly one "ana"
test_signup_weak_password        # password "12345678" -> 200, no user created
test_login_ok                    # POST /accounts/login/ -> 302 to "/"; session has the user
test_login_wrong_password        # -> 200; session has no user
test_logout_is_post_only         # GET /accounts/logout/ -> 405; POST -> 302 to "/" and session has no user
test_header_logged_out           # GET "/" contains "Log in" and "Sign up"
test_header_logged_in            # after login, GET "/" with follow=True contains "ana" and "Log out"
                                 # (follow=True because chunk 3 makes "/" redirect a logged-in user)
test_logged_in_user_skips_signup_and_login   # GET either page while logged in -> 302 to "/"
```

- [x] **Step 2: Run and see them fail**

Run: `.venv\Scripts\python.exe manage.py test accounts`
Expected: failures; the addresses do not exist.

- [x] **Step 3: Add the user model** (skip if D1 = a)

`accounts/models.py`: `class User(AbstractUser): pass`. `config/settings.py`: `AUTH_USER_MODEL = "accounts.User"`. `accounts/admin.py`: register it with Django's `UserAdmin`.

- [x] **Step 4: Implement the pages**

- `accounts/forms.py`: `SignupForm(UserCreationForm)` with `Meta.model = get_user_model()` and `fields = ("username",)`.
- `accounts/views.py`: `signup(request)`. GET shows the form. A valid POST saves the user, calls `login(request, user)`, adds the message "Welcome, ana." and redirects to `home`. A logged-in visitor is redirected to `home`.
- `accounts/urls.py`: `signup/` → `views.signup`; `login/` → Django's `LoginView` with `redirect_authenticated_user=True`; `logout/` → Django's `LogoutView`.
- Templates extend `base.html` and show field errors next to each field.
- `templates/base.html` header: logged in → the username and a "Log out" button inside a small POST form; logged out → "Log in" and "Sign up" links, using `{% url %}`.

- [x] **Step 5: Make the database**

```powershell
.venv\Scripts\python.exe manage.py makemigrations accounts
.venv\Scripts\python.exe manage.py migrate
```

Expected: `accounts/migrations/0001_initial.py` is created and all migrations apply.

- [x] **Step 6: Run all tests and see them pass**

Run: `.venv\Scripts\python.exe manage.py test`
Expected: 16 tests, OK (15 if D1 = a).

- [ ] **Step 7: Commit point**

```powershell
git add accounts config templates
git commit -m "Accounts: own user model, sign-up, login, logout"
```

## Walk through (chunk 1)

**Trace:** signing up as a new user. Browser `POST /accounts/signup/` → `config/urls.py` → `accounts/urls.py` → `views.signup` → `SignupForm.is_valid()` (where the password rules run) → `form.save()` (the password is stored hashed) → `login()` (a session row and a cookie) → redirect → `rooms.views.home` → `base.html` shows the username.

**The builder runs:**
1. `.venv\Scripts\python.exe manage.py runserver`, opens `http://127.0.0.1:8000/`, signs up, logs out, logs in.
2. `.venv\Scripts\python.exe manage.py createsuperuser`, then opens `/admin/` and finds both users. Point out that the password column is a hash.
3. Opens `.secret_key` and `.gitignore` side by side and says why the key is not in git.
4. In PyCharm: set the project interpreter to `.venv\Scripts\python.exe`.

## Record (chunk 1)

Create `docs/system-map.md`. Give it a short introduction (what the app is, how to run it and its tests) and then one section per piece, each with the same five headings: **What it does · Where the code is · How one request flows · Decisions and why (who decided, when) · How to change it**. Write the sections "Project and settings" and "Accounts". Record D1 as the builder's decision and every "Claude's call" above as Claude's.

## As built (chunk 1, 16 Nov 2026)

Chunk 1 ended with **50 tests**, all passing, against the 16 this plan listed. The later counts in this plan have been raised to match. Where the build departs from the text above, the build is right and this list says why:

- **Git.** The repository already existed (the builder made it at 13:41 on 16 Nov, branch `master`, with `docs/` and `.idea/` committed). `git init -b main` did nothing. The branch stays `master`, and `.idea/` was left out of `.gitignore` because the builder tracks it.
- **Secret key.** Made with Python's `secrets.token_urlsafe(50)` instead of Django's `get_random_secret_key()`, so `config/secret.py` needs nothing from Django's management code while settings load. Nine tests were added beyond the three listed: a blank environment variable, a blank key file, stray whitespace, a byte-order mark, a UTF-16 file, an unwritable folder.
- **`DJANGO_ALLOWED_HOSTS`** was added to the settings. Without it, `DJANGO_DEBUG=0` refuses every request.
- **`MEDIA_URL = "/media/"`** was set so file links in the admin are well-formed. Nothing serves that address.
- **`templates/includes/form_fields.html`** draws every form's fields. Later chunks use it.
- **`templates/404.html` and `templates/500.html`** exist. Chunk 3 does not need to make a not-found page.
- **Tests use a fast password hasher** (`settings.py`, only when the command is `test`). With real hashing the suite took 15 seconds.
- **The header tests** read only the `<header>` part of the page, because the home page body also links to sign-up and login.
- **Extra account tests:** sign-up cannot create a staff account; usernames differing only in case are refused; a login `next` pointing at another site is ignored; the username in the header is escaped.

Checked by hand against the running server on 16 Nov: sign-up, login and logout through real requests; a POST without the security token gets a 403; logout by GET gets a 405; the eight ways a sign-up can be refused each show their message; an accented username is accepted; with debug off, an unknown address shows our not-found page and a wrong host name gets a 400.

Committed as one commit, `4ed4bda` "Chunk 1: project skeleton and accounts", instead of the two commit points above, because both tasks were finished before the builder was asked. Not done: the walk-through (it needs the builder).

---

# Chunk 2: The four models

**Ends with:** the database holds places, scans, memories and pins with every rule from §6, and the builder can see and edit them in the admin.

## Decide

**Builder's decisions:** none. The model was approved on 16 Nov (§6 of the spec).

**Claude's calls** (read them out):
- A place's address word (its slug) is made once, when the place is created, and does not change if the place is renamed, so old links keep working.
- If the owner already has that slug, or it is the reserved word `new`, a number is added: `dorm-room`, `dorm-room-2`.
- Uploaded files are stored under a generated name, `places/<place id>/...`, never under the name the phone gave them.
- The pin rules run every time a pin is saved, from any code path, not only from forms.
- Pin coordinates must be real numbers. A failed placement run can produce "not a number"; that is refused.
- Three small migrations, one per task, named for what they add.

## Task 3: Place and its slug

**Files:**
- Create: `rooms/slugs.py`, `rooms/tests/utils.py`, `rooms/tests/test_models.py`, `rooms/migrations/0001_place.py` (generated)
- Modify: `rooms/models.py`, `rooms/admin.py`

**Interfaces:**
- Produces: `Place(owner, name, slug, created)`; `rooms.slugs.unique_slug(owner, name: str) -> str`; `rooms.slugs.RESERVED = {"new"}`; test helper `make_user(username="ana", password="pass-12345-word") -> User`.

- [ ] **Step 1: Write the failing tests** (`rooms/tests/test_models.py`, class `PlaceTests`)

```python
test_slug_made_from_name             # name "Dorm Room 214" -> slug "dorm-room-214"
test_same_name_same_owner_numbered   # three places named "Dorm Room" -> "dorm-room", "dorm-room-2", "dorm-room-3"
test_same_name_two_owners            # ana and ben each get "dorm-room"
test_reserved_word                   # name "New" -> slug "new-2"
test_name_without_letters            # name "🏠🏠" -> slug "place"; a second one -> "place-2"
test_long_name                       # an 80-character name -> slug of at most 70 characters, no trailing "-"
test_slug_kept_on_rename             # rename "Dorm Room" to "Old Dorm", save -> slug still "dorm-room"
test_str_is_name
```

- [ ] **Step 2: Run and see them fail** — `.venv\Scripts\python.exe manage.py test rooms.tests.test_models`

- [ ] **Step 3: Implement**

```python
class Place(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="places")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, editable=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        constraints = [models.UniqueConstraint(fields=["owner", "slug"], name="unique_slug_per_owner")]
```

`Place.save()` sets `self.slug = unique_slug(self.owner, self.name)` only when the slug is empty. `unique_slug`: Django's `slugify(name)`, cut to 70 characters and stripped of trailing hyphens; `"place"` if that is empty; then add `-2`, `-3`, … while the word is in `RESERVED` or this owner already uses it. Register `Place` in the admin showing name, owner, slug, created.

- [ ] **Step 4: Migrate and pass**

```powershell
.venv\Scripts\python.exe manage.py makemigrations rooms -n place
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test rooms.tests.test_models
```

Expected: 8 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Place model with per-owner slugs"`

## Task 4: Scan, Memory and their files

**Files:**
- Create: `rooms/signals.py`, `rooms/migrations/0002_scan_memory.py` (generated)
- Modify: `rooms/models.py`, `rooms/apps.py`, `rooms/admin.py`, `rooms/tests/utils.py`, `rooms/tests/test_models.py`

**Interfaces:**
- Consumes: `Place`, `make_user`.
- Produces:
  - `Scan(place, video, taken_on, status, points_file, created)` with `Scan.Status.UPLOADED / BUILDING / READY / FAILED` (stored as `"uploaded"`, `"building"`, `"ready"`, `"failed"`).
  - `Memory(place, photo, caption, taken_on, created)`.
  - `Place.newest_ready_scan() -> Scan | None`. No page in this plan calls it; the viewer page will.
  - Related names: `place.scans`, `place.memories`.
  - Test helpers in `rooms/tests/utils.py`: `TempMediaTestCase` (a `TestCase` whose `MEDIA_ROOT` is a temporary folder, removed afterwards); `jpeg_file(name="photo.jpg", taken=None) -> SimpleUploadedFile` (a real 8×8 JPEG made with Pillow; `taken` is a `datetime` written into the photo as its capture date); `video_file(name="room.mp4", size=64) -> SimpleUploadedFile` (bytes that start `\x00\x00\x00\x18ftypmp42`, padded with zeros to `size`).

- [ ] **Step 1: Write the failing tests** (classes `ScanTests`, `MemoryTests`, `FileTests`, all on `TempMediaTestCase`)

```python
test_scan_defaults                 # new scan: status "uploaded", taken_on == timezone.localdate(), points_file empty
test_newest_ready_scan             # scans: ready (1 Sep), ready (1 Nov), uploaded (10 Nov), failed (12 Nov) -> the 1 Nov one
test_newest_ready_scan_none        # only an uploaded scan -> None
test_memory_optional_fields        # caption "" and taken_on None are valid (full_clean passes)
test_memory_order                  # dated 9 May, dated 1 Mar, undated -> that order
test_stored_name_is_generated
    # photo uploaded as "../../my room 🏠.JPG" -> memory.photo.name matches
    # r"^places/\d+/memories/[0-9a-f]{32}\.jpg$"
test_video_stored_name             # "Room Video.MP4" -> r"^places/\d+/scans/[0-9a-f]{32}\.mp4$"
test_long_file_name                # a 200-character file name saves without error
test_delete_memory_removes_file    # the file exists on disk; after memory.delete() it does not
test_delete_scan_removes_files     # video and points_file both gone from disk
test_delete_place_removes_rows_and_files
    # a place with 1 scan and 2 memories: after place.delete(), Scan and Memory counts are 0
    # and none of the three files exist
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement**

```python
class Scan(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        BUILDING = "building", "Building"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="scans")
    video = models.FileField(upload_to=scan_video_path)
    taken_on = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UPLOADED)
    points_file = models.FileField(upload_to=scan_points_path, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_on", "-created"]


class Memory(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="memories")
    photo = models.ImageField(upload_to=memory_photo_path)
    caption = models.CharField(max_length=200, blank=True)
    taken_on = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "memories"
        ordering = [models.F("taken_on").desc(nulls_last=True), "-created"]
```

The three path functions are module-level functions in `rooms/models.py` with the signature `(instance, filename) -> str`. They return `places/<place_id>/scans/<uuid4 hex><ext>`, `places/<place_id>/scans/<uuid4 hex>-points.bin` and `places/<place_id>/memories/<uuid4 hex><ext>`, where `<ext>` is the lower-cased extension of the original name and nothing else from it is used.

`rooms/signals.py`: two `post_delete` receivers, one for `Scan` (deletes `video` and `points_file`) and one for `Memory` (deletes `photo`), each with `field.delete(save=False)` and skipping empty fields. Import the module in `RoomsConfig.ready()`. Register both models in the admin.

- [ ] **Step 4: Migrate and pass**

```powershell
.venv\Scripts\python.exe manage.py makemigrations rooms -n scan_memory
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test rooms.tests.test_models
```

Expected: 19 tests, OK. Confirm no files were left in the real `media/` folder by the tests.

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Scan and Memory models, generated file names, file clean-up on delete"`

## Task 5: Pin and its rules

**Files:**
- Create: `rooms/migrations/0003_pin.py` (generated)
- Modify: `rooms/models.py`, `rooms/admin.py`, `rooms/tests/test_models.py`

**Interfaces:**
- Consumes: `Scan`, `Memory`, the test helpers.
- Produces: `Pin(memory, scan, x, y, z, placed_by, created)` with `Pin.PlacedBy.USER / AI` (stored as `"user"`, `"ai"`); related names `memory.pins`, `scan.pins`. Saving an invalid pin raises `django.core.exceptions.ValidationError`.

- [ ] **Step 1: Write the failing tests** (class `PinTests`)

```python
test_pin_in_same_place_saves          # x=1.62, y=1.08, z=1.41, placed_by="user" -> saved, values read back
test_pin_across_places_refused        # memory in place A, scan in place B -> ValidationError
test_second_pin_same_scan_refused     # same memory and scan twice -> ValidationError, still one row
test_one_pin_per_scan_allowed         # one memory, two scans of the same place, a pin in each -> two rows
test_placed_by_must_be_stated         # placed_by "" -> ValidationError; "none" -> ValidationError
test_coordinates_must_be_numbers      # x = float("nan") -> ValidationError; z = float("inf") -> ValidationError
test_delete_scan_removes_pins_keeps_memory
test_delete_memory_removes_pins
test_delete_place_removes_pins
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement**

```python
class Pin(models.Model):
    class PlacedBy(models.TextChoices):
        USER = "user", "User"
        AI = "ai", "AI"

    memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name="pins")
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="pins")
    x = models.FloatField()
    y = models.FloatField()
    z = models.FloatField()
    placed_by = models.CharField(max_length=4, choices=PlacedBy.choices)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["memory", "scan"], name="one_pin_per_memory_per_scan")]
```

`Pin.clean()` raises `ValidationError` when the memory's place and the scan's place differ ("A pin's photo and scan must belong to the same place.") or when any of x, y, z fails `math.isfinite`. `Pin.save()` calls `self.full_clean()` first, so the rules hold from the admin, the shell and any later import script. Register `Pin` in the admin.

- [ ] **Step 4: Migrate and pass**

```powershell
.venv\Scripts\python.exe manage.py makemigrations rooms -n pin
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test
```

Expected: 78 tests, OK (50 from chunk 1, 28 model tests).

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Pin model: one per memory per scan, same place, real coordinates"`

## Walk through (chunk 2)

**Trace:** saving a pin. `Pin.save()` → `full_clean()` → field checks (`placed_by` is one of two words) → `clean()` (same place, real numbers) → the unique rule → `INSERT`.

**The builder runs:**
1. In `/admin/`: make two places with the same name and compare their slugs. Add a memory with a photo and find the file under `media/places/`.
2. In the admin, try to add a pin whose memory and scan are in different places, then a second pin for the same memory and scan. Read both error messages.
3. Delete a place in the admin and watch its files leave `media/`.
4. `.venv\Scripts\python.exe manage.py sqlmigrate rooms 0003` to see the real table and its unique rule.
5. Open `rooms/models.py` next to §6 of the spec and match every line.

## Record (chunk 2)

Add "Data model" to `docs/system-map.md`: a diagram of the four models and their links, each rule from §6 with the line of code that enforces it and the test that proves it, and the reasons from §6 (why Pin is its own model: the builder's decision of 16 Nov). Add the calls listed in this chunk's Decide block.

---

# Chunk 3: Places pages

**Ends with:** a logged-in person can create, list, open, rename and delete places. This is the database-backed workflow the first-draft rubric asks for: form → view → database → visible result.

## Decide

**Builder's decisions:** none new. "Each user sees only their own places" is in the spec.

**Claude's calls** (read them out):
- Another user's place answers 404, the same as a place that does not exist, so nobody can learn which addresses are taken.
- Deleting a place asks first, on a page that says how many scans and photos will go with it.
- Renaming a place does not change its address.
- A logged-in person who opens `/` is sent to their list of places.

## Task 6: List, create and open a place

**Files:**
- Create: `rooms/access.py`, `rooms/forms.py`, `rooms/tests/test_places.py`, `rooms/templates/rooms/place_list.html`, `place_form.html`, `place_detail.html`
- Modify: `rooms/views.py`, `rooms/urls.py`, `rooms/models.py`, `rooms/tests/test_home.py`

**Interfaces:**
- Consumes: `Place`, `make_user`.
- Produces:
  - `rooms.access.get_own_place(user, slug: str) -> Place` (raises `Http404`).
  - `rooms.forms.PlaceForm` (a `ModelForm` with the one field `name`).
  - URL names: `place_list` (`/places/`), `place_create` (`/places/new/`), `place_detail` (`/places/<slug>/`).
  - `Place.get_absolute_url()` → the `place_detail` address.
  - `place_detail.html` has two sections with the headings "Room scans" and "Photos"; chunks 4 and 5 fill them.

- [ ] **Step 1: Write the failing tests** (`rooms/tests/test_places.py`)

```python
test_pages_need_login          # logged out: GET /places/, /places/new/, /places/x/ -> 302 to /accounts/login/?next=<path>
test_list_shows_only_mine      # ana has "Dorm", ben has "Flat": ana's list contains "Dorm" and not "Flat"
test_empty_list                # contains "No places yet" and a link to /places/new/
test_create_place
    # POST name="Dorm Room 214" -> 302 to /places/dorm-room-214/; the place's owner is ana;
    # following the redirect shows "Dorm Room 214" and the message "Place created."
test_create_blank_name         # name "   " -> 200, no place, an error on the name field
test_create_long_name          # 81 characters -> 200, no place
test_open_other_users_place    # ben GETs ana's /places/dorm/ -> 404
test_same_slug_two_owners      # each of ana and ben sees their own "dorm-room" page
test_name_shown_as_text        # name "<b>x</b>" -> the page contains "&lt;b&gt;x&lt;/b&gt;"
test_home_redirects_when_logged_in   # GET "/" logged in -> 302 to /places/   (in test_home.py)
```

- [ ] **Step 2: Run and see them fail** — `.venv\Scripts\python.exe manage.py test rooms.tests.test_places`

- [ ] **Step 3: Implement**

- `rooms/access.py`: `get_own_place(user, slug)` is `get_object_or_404(Place, owner=user, slug=slug)`. This one line is the privacy rule for the whole app; give it a comment that says so.
- `rooms/urls.py`: list `places/new/` **before** `places/<slug:slug>/`.
- Views `place_list`, `place_create`, `place_detail`, each with `@login_required`. `place_create` sets `form.instance.owner = request.user` before saving. `home` redirects a logged-in user to `place_list`.
- `place_detail.html` for now:

```
Dorm Room 214                         Rename · Delete
Created 16 Nov 2026

Room scans
  No room video yet.

Photos
  No photos yet.
```

(The Rename and Delete links arrive in Task 7; the buttons in each section arrive in chunks 4 and 5.)

- [ ] **Step 4: Run all tests and see them pass** — expected: 88 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Places: list, create, open, owner-only"`

## Task 7: Rename and delete a place

**Files:**
- Create: `rooms/templates/rooms/place_confirm_delete.html`
- Modify: `rooms/views.py`, `rooms/urls.py`, `rooms/templates/rooms/place_detail.html`, `rooms/tests/test_places.py`

**Interfaces:**
- Consumes: `get_own_place`, `PlaceForm`.
- Produces: URL names `place_edit` (`/places/<slug>/edit/`), `place_delete` (`/places/<slug>/delete/`).

- [ ] **Step 1: Write the failing tests**

```python
test_rename                     # POST name="Old Dorm" to /places/dorm-room/edit/ -> 302 to /places/dorm-room/;
                                # name is "Old Dorm", slug still "dorm-room", message "Place renamed."
test_rename_blank               # -> 200, name unchanged
test_delete_asks_first          # GET /places/dorm-room/delete/ -> 200, contains the name; the place still exists
test_delete                     # POST -> 302 to /places/; the place is gone; message "Place deleted."
test_delete_page_counts         # a place with 1 scan and 2 memories: the page contains "1 room video" and "2 photos"
test_other_user_cannot_rename   # ben POSTs to ana's edit address -> 404; name unchanged
test_other_user_cannot_delete   # ben POSTs to ana's delete address -> 404; the place still exists
test_edit_delete_need_login     # logged out -> 302 to login
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement** views `place_edit` (reuses `place_form.html`) and `place_delete` (GET shows the confirmation, POST deletes). Add the Rename and Delete links to `place_detail.html`.

- [ ] **Step 4: Run all tests and see them pass** — expected: 96 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Places: rename and delete with confirmation"`

## Walk through (chunk 3)

**Trace:** creating a place called "Dorm Room 214". `POST /places/new/` → `config/urls.py` → `rooms/urls.py` → `views.place_create` → `@login_required` → `PlaceForm.is_valid()` → `owner` set from `request.user` → `Place.save()` → `slugs.unique_slug()` → `INSERT` → redirect to `/places/dorm-room-214/` → `views.place_detail` → `access.get_own_place()` → `place_detail.html`.

**The builder runs:**
1. Creates a place, renames it, and checks the address did not change.
2. Signs up a second user in a private window, pastes the first user's place address, and gets a 404. Then finds the one line in `rooms/access.py` that caused it.
3. Creates a place named "New" and looks at its address.
4. `.venv\Scripts\python.exe manage.py shell`, then `from rooms.models import Place; list(Place.objects.values("owner__username", "name", "slug"))`.

## Record (chunk 3)

Add "Places" to the system map with the traced request, the table of addresses, and the owner-check rule (where it lives, why 404 and not 403).

---

# Chunk 4: Room video upload

**Ends with:** a person can add a room video to a place, see it listed with its status, and delete it.

## Decide

**Builder's decisions:** none new; the Scan model and "the video is kept for now" are approved in §6.

**Claude's calls** (read them out, with the numbers; the builder may want to change them):
- Videos must be MP4 or MOV, checked two ways: the file name's ending and the first bytes of the file itself.
- The size limit is 500 MB. A Galaxy S23 FE at 1080p writes roughly 130 MB a minute, so this allows about three minutes; 4K would hit the limit in under two. The form says "Film at 1080p. One to two minutes is enough."
- The filming date starts as today and can be changed, but not to a future date.
- A scan stays at "Uploaded" in this plan. Nothing in the app builds the 3D room yet, and the page says so plainly.
- A place can hold several scans; they are listed newest first.

## Task 8: Video checks and the scan form

**Files:**
- Create: `rooms/validators.py`, `rooms/tests/test_scans.py`
- Modify: `rooms/forms.py`, `config/settings.py`

**Interfaces:**
- Consumes: `Scan`, `video_file`, `jpeg_file`.
- Produces: setting `MAX_VIDEO_BYTES = 500 * 1024 * 1024`; `rooms.validators.validate_video(file) -> None` (raises `ValidationError`); `rooms.forms.ScanForm` (a `ModelForm` with fields `video`, `taken_on`).

- [ ] **Step 1: Write the failing tests** (class `ScanFormTests`; build the form with `ScanForm(data, files)`)

```python
test_valid_mp4                 # video_file("room.mp4") -> valid
test_upper_case_ending         # "ROOM.MP4" -> valid
test_mov_accepted              # "room.mov" with the same leading bytes -> valid
test_long_file_name_accepted   # a 150-character name ending ".mp4" -> valid
test_wrong_ending              # "notes.txt" -> error "Upload an MP4 or MOV video."
test_wrong_content             # a JPEG renamed "room.mp4" -> error "This file is not a video the app can read."
test_too_large                 # with MAX_VIDEO_BYTES=10 -> an error containing "too large"
test_empty_file                # zero bytes -> not valid
test_no_file                   # -> error "This field is required."
test_future_date               # taken_on = tomorrow -> error "The date can't be in the future."
test_date_defaults_to_today    # the unbound form's initial taken_on is timezone.localdate()
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement**

`validate_video(file)` checks, in this order: the ending is `.mp4` or `.mov` (any case); `file.size <= settings.MAX_VIDEO_BYTES` (message: "This video is too large. The limit is 500 MB.", with the number taken from the setting); bytes 4 to 8 of the file are `b"ftyp"`. It must leave the file rewound to the start. `ScanForm` declares `video` itself as `forms.FileField(validators=[validate_video])` rather than taking the field the model would generate: the generated one refuses any file whose original name is longer than 100 characters, and the original name is never stored. The input carries `accept="video/mp4,video/quicktime"`, and `taken_on` renders as a date input.

- [ ] **Step 4: Run and see them pass** — expected: 107 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms config` · `git commit -m "Video checks and scan form"`

## Task 9: Upload and delete pages for scans

**Files:**
- Create: `rooms/templates/rooms/scan_form.html`, `scan_confirm_delete.html`
- Modify: `rooms/access.py`, `rooms/views.py`, `rooms/urls.py`, `rooms/templates/rooms/place_detail.html`, `rooms/tests/test_scans.py`

**Interfaces:**
- Consumes: `get_own_place`, `ScanForm`.
- Produces: `rooms.access.get_own_scan(user, pk: int) -> Scan`; URL names `scan_create` (`/places/<slug>/scans/new/`), `scan_delete` (`/scans/<pk>/delete/`).

- [ ] **Step 1: Write the failing tests** (class `ScanPageTests` on `TempMediaTestCase`)

```python
test_pages_need_login
test_upload
    # POST a video to /places/dorm/scans/new/ -> 302 to /places/dorm/; one Scan, status "uploaded",
    # its file exists on disk; the place page contains "Uploaded" and the message "Room video added."
test_upload_with_date          # taken_on 2026-09-01 -> stored; the place page shows "1 Sep 2026"
test_upload_bad_file           # a .txt file -> 200, no Scan, the error text is on the page
test_upload_to_other_users_place   # ben GETs and POSTs to ana's address -> 404, no Scan
test_two_scans_newest_first    # filmed 1 Sep and 1 Nov -> the 1 Nov line comes first on the page
test_delete_asks_first         # GET /scans/<pk>/delete/ -> 200; the scan still exists
test_delete                    # POST -> 302 to the place page; row and file gone; message "Room video deleted."
test_other_user_cannot_delete  # -> 404; the scan still exists
test_no_scans_text             # a place with no scans shows "No room video yet."
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement**

`get_own_scan(user, pk)` is `get_object_or_404(Scan, pk=pk, place__owner=user)`. `scan_create` sets `form.instance.place` from `get_own_place`. The form template carries `enctype="multipart/form-data"`. The "Room scans" section of the place page becomes:

```
Room scans                                  [Add a room video]
  Filmed 1 Nov 2026 · Uploaded · Delete
  Filmed 1 Sep 2026 · Uploaded · Delete
  Uploaded videos wait here. Building the 3D room is not part of the app yet.
```

- [ ] **Step 4: Run all tests and see them pass** — expected: 117 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Scans: upload and delete a room video"`

## Walk through (chunk 4)

**Trace:** uploading a room video. `POST /places/<slug>/scans/new/` (a multipart request: Django writes the large file to a temporary file as it arrives) → `views.scan_create` → `get_own_place` → `ScanForm.is_valid()` → `validate_video` → `Scan.save()` → `scan_video_path` picks the name → the file moves into `media/places/<id>/scans/` → redirect → place page.

**The builder runs:**
1. Uploads the real video of their room (this is also Monday's "the builder films the room" from the spec). Notes how long the upload took.
2. Finds the file under `media/` and the row in `/admin/`; compares the stored name with the phone's name for it.
3. Renames a photo to `fake.mp4`, tries to upload it and reads the message. Then finds the three checks in `rooms/validators.py`.
4. Deletes a scan and confirms the file left the disk.

## Record (chunk 4)

Add "Room video upload" to the system map: the traced request, the three checks and their numbers, where files live and how they are named, and the honest status note (nothing builds the room yet; the Colab run is a separate piece).

## As built (chunks 2, 3 and 4, 17 Nov 2026)

The code for all three chunks came from `prebuilt/django/chunk2-models`, `chunk3-places` and `chunk4-video`, applied one after another with `kit.py apply --write`. Nothing was written by hand.

- **Why without the builder.** On 17 Nov the builder said they could not give time to the docs yet and asked Claude to start working. The Decide step's calls (this plan's, plus each kit README's "Calls made here") were therefore not read out first, and the three walk-throughs were not done. Both are owed. Nothing is committed, so any call the builder overrules is a plain edit.
- **Before.** `kit.py verify --upto chunk4-video` on a fresh copy: check, migrations and tests all `ok` (123 tests). The project's own suite: 50 pass.
- **After each apply** (`migrate`, then `test`): 78, then 99, then 123 tests, all passing, as the kits' READMEs predicted. `makemigrations --check` reports no changes. Migrations `0001_place`, `0002_scan_memory` and `0003_pin` were applied to the builder's `db.sqlite3`.
- **Counts against this plan.** 99 after chunk 3 (the plan says 96) and 123 after chunk 4 (the plan says 117): the six extra tests are listed in the two kits' READMEs.
- **Checked against a running server.** A throwaway copy of the app with its own database ran real HTTP requests: 20 of 20 checks passed (list in `docs/system-map.md`, "Running it"). The video was a 64-byte stand-in. The real room video and a browser look are the walk-throughs' job.
- **Recorded.** Pieces 3, 4 and 5 in `docs/system-map.md` are the kits' drafts, with a status line added to each. The kits' folders under `prebuilt/` are kept until the builder has walked through and committed.

---

# Chunk 5: Photos

**Ends with:** a person can add many photos to a place at once, caption them, change their dates and delete them; nobody else can fetch a photo.

## Decide

**Builder's decision D2: how photos are added.**

| | Option | Trade-off |
| --- | --- | --- |
| **a (recommended)** | Pick many photos in one go; add captions afterwards, photo by photo | Fits the product (people have dozens of photos of a room). Needs a small custom form field |
| b | One photo per form, with its caption on the same form | The simplest Django code. Slow for thirty photos |

**If the builder picks b:** in Task 10, replace `MultipleImageField` and `MemoryUploadForm` with a `ModelForm` on `photo`, `caption`, `taken_on`; drop the "many files" tests; the message becomes "Photo added."

**Builder's decision D3: who can fetch a photo file.**

| | Option | Trade-off |
| --- | --- | --- |
| **a (recommended)** | Every photo is served by a Django view that checks the owner first | Matches "private by default". Each image request runs Python, which is fine at this size. At deployment this becomes time-limited bucket links |
| b | Photos sit at open addresses with long random names | Less code and faster. Anyone who has the link sees the photo, logged in or not |

**If the builder picks b:** drop the `memory_photo` view and its tests in Task 11, serve `media/` with Django's `static()` helper while `DEBUG` is on, and use `memory.photo.url` in the template.

**Claude's calls** (read them out):
- JPEG, PNG and WebP only, 20 MB each, at most 50 per upload. iPhone HEIC photos get a clear message instead of a crash.
- If one file in a batch is bad, none are saved and the message names the bad file. (Saving the good ones and skipping the bad is the friendlier behaviour; it is a later improvement.)
- The date is read from inside the photo when it has one, and left empty otherwise. It can be edited.
- Location data inside photos is left as it is for now. Stripping it is in the technical design's privacy list and belongs with the security work.
- The grid shows the full-size photo scaled down, loaded lazily. Real thumbnails are a later improvement; a place with many large photos will be slow to scroll.

## Task 10: Photo checks, date reading and the upload form

**Files:**
- Create: `rooms/photos.py`, `rooms/tests/test_memories.py`
- Modify: `rooms/validators.py`, `rooms/forms.py`, `config/settings.py`

**Interfaces:**
- Consumes: `Memory`, `jpeg_file`.
- Produces:
  - Settings `MAX_PHOTO_BYTES = 20 * 1024 * 1024`, `MAX_PHOTOS_PER_UPLOAD = 50`.
  - `rooms.photos.photo_taken_on(file) -> datetime.date | None`. Never raises. Leaves the file rewound.
  - `rooms.validators.validate_photo(file) -> None`.
  - `rooms.forms.MultipleImageField`, and `rooms.forms.MemoryUploadForm` whose `cleaned_data["photos"]` is a list of checked files.
  - `rooms.forms.MemoryForm` (a `ModelForm` with `caption`, `taken_on`).

- [ ] **Step 1: Write the failing tests** (classes `PhotoDateTests`, `MemoryFormTests`)

```python
test_date_read_from_photo          # jpeg_file(taken=datetime(2026, 5, 9, 14, 3)) -> date(2026, 5, 9)
test_no_date_in_photo              # jpeg_file() -> None
test_garbled_date                  # a JPEG whose date text is "not a date" -> None, no exception
test_not_an_image                  # photo_taken_on on text bytes -> None, no exception
test_file_left_rewound             # after the call, file.tell() == 0

test_one_photo_valid
test_three_photos_valid            # cleaned_data["photos"] has 3 items
test_text_file_named_jpg           # -> not valid; the error names the file "notes.jpg"
test_one_bad_in_three              # -> not valid; the error names only the bad file
test_gif_refused                   # a real GIF -> "Upload JPEG, PNG or WebP photos. HEIC is not supported yet."
test_heic_refused                  # bytes named "IMG_0001.heic" -> not valid, no exception
test_too_large                     # with MAX_PHOTO_BYTES=10 -> an error containing "too large"
test_too_many                      # with MAX_PHOTOS_PER_UPLOAD=2 and 3 files -> "Upload at most 2 photos at a time."
test_no_files                      # -> "This field is required."
test_caption_too_long              # MemoryForm with 201 characters -> not valid
test_future_date_refused           # MemoryForm taken_on = tomorrow -> "The date can't be in the future."
test_date_can_be_cleared           # MemoryForm taken_on "" -> valid, None
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement**

- `photo_taken_on`: open with Pillow; read the capture date (Exif tag 36867, `DateTimeOriginal`, inside the Exif block 0x8769); fall back to tag 306 (`DateTime`); parse `"%Y:%m:%d %H:%M:%S"`; return the date. Any exception at all returns `None`.
- `validate_photo`: size against `MAX_PHOTO_BYTES` ("This photo is too large. The limit is 20 MB."), then the format Pillow detected is one of JPEG, PNG, WEBP.
- `MultipleImageField`: follow the "Uploading multiple files" pattern in the Django 5.2 documentation (a `ClearableFileInput` subclass with `allow_multiple_selected = True`, and a field whose `clean` accepts a list). Run Django's `forms.ImageField` check and then `validate_photo` on each file, collect every failure as `"<file name>: <message>"`, and raise them together. Enforce `MAX_PHOTOS_PER_UPLOAD`. The input carries `accept="image/jpeg,image/png,image/webp"`.

- [ ] **Step 4: Run and see them pass** — expected: 134 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms config` · `git commit -m "Photo checks, date reading, multi-photo form"`

## Task 11: Add photos, show them, serve them privately

**Files:**
- Create: `rooms/templates/rooms/memory_upload.html`
- Modify: `rooms/access.py`, `rooms/views.py`, `rooms/urls.py`, `rooms/templates/rooms/place_detail.html`, `static/css/site.css`, `rooms/tests/test_memories.py`

**Interfaces:**
- Consumes: `get_own_place`, `MemoryUploadForm`, `photo_taken_on`.
- Produces: `rooms.access.get_own_memory(user, pk: int) -> Memory`; URL names `memory_create` (`/places/<slug>/memories/new/`), `memory_photo` (`/memories/<pk>/photo/`).

- [ ] **Step 1: Write the failing tests** (class `MemoryPageTests` on `TempMediaTestCase`)

```python
test_pages_need_login              # the upload page and the photo address -> 302 to login
test_upload_one                    # -> 302 to the place page; one Memory; file on disk; message "1 photo added."
test_upload_three                  # -> three Memory rows; message "3 photos added."
test_date_filled_from_photo        # a photo taken 9 May 2026 -> memory.taken_on == date(2026, 5, 9)
test_undated_photo                 # -> taken_on is None; the upload still succeeds
test_bad_batch_saves_nothing       # two good and one bad -> 200, zero rows, no new files on disk
test_upload_to_other_users_place   # -> 404, zero rows
test_place_page_shows_photos       # two memories -> the page contains "Photos (2)" and both photo addresses
test_other_users_photos_not_listed # ben's place page never contains ana's photo addresses
test_photo_served_to_owner         # GET /memories/<pk>/photo/ -> 200, Content-Type "image/jpeg", the same bytes
test_photo_refused_to_others       # ben -> 404
test_photo_file_missing            # delete the file from disk, keep the row -> the photo address gives 404
                                   # and the place page still gives 200
test_media_folder_not_public       # GET /media/<the stored path> -> 404
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement**

- `memory_create`: inside `transaction.atomic()`, one `Memory` per file with `taken_on=photo_taken_on(file)`. The message uses "1 photo" / "N photos".
- `memory_photo`: `get_own_memory`, then a `FileResponse` of the opened file with the header `Cache-Control: private, max-age=3600`. A missing file (`FileNotFoundError`) becomes `Http404`.
- Do **not** add a `media/` route to `config/urls.py`.
- The "Photos" section of the place page:

```
Photos (3)                                      [Add photos]
  ┌─────┐  ┌─────┐  ┌─────┐
  │ img │  │ img │  │ img │      each image: src = the memory_photo address, loading="lazy"
  └─────┘  └─────┘  └─────┘
  Move-in day   (no caption)   Last night
  9 May 2026    no date        1 Nov 2026
```

- [ ] **Step 4: Run all tests and see them pass** — expected: 147 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms static` · `git commit -m "Memories: upload many photos, private photo serving, photo grid"`

## Task 12: Caption, date and delete

**Files:**
- Create: `rooms/templates/rooms/memory_form.html`, `memory_confirm_delete.html`
- Modify: `rooms/views.py`, `rooms/urls.py`, `rooms/templates/rooms/place_detail.html`, `rooms/tests/test_memories.py`

**Interfaces:**
- Consumes: `get_own_memory`, `MemoryForm`.
- Produces: URL names `memory_edit` (`/memories/<pk>/edit/`), `memory_delete` (`/memories/<pk>/delete/`). Each photo in the grid links to its `memory_edit` page.

- [ ] **Step 1: Write the failing tests** (class `MemoryEditTests`)

```python
test_edit_page_shows_photo         # GET -> 200, contains the photo address and the current caption
test_save_caption                  # POST caption="Move-in day" -> 302 to the place page; the page shows it;
                                   # message "Photo updated."
test_caption_shown_as_text         # caption "<script>alert(1)</script>" -> the place page contains "&lt;script&gt;"
test_change_date                   # taken_on 2026-08-20 -> stored
test_other_user_cannot_edit        # GET and POST -> 404; caption unchanged
test_delete_asks_first             # GET -> 200; the memory still exists
test_delete                        # POST -> 302 to the place page; row and file gone; message "Photo deleted."
test_other_user_cannot_delete      # -> 404; the memory still exists
test_edit_delete_need_login
```

- [ ] **Step 2: Run and see them fail**

- [ ] **Step 3: Implement** views `memory_edit` (the photo above the form) and `memory_delete`, and link each grid photo to its edit page.

- [ ] **Step 4: Run all tests and see them pass** — expected: 156 tests, OK.

- [ ] **Step 5: Commit point** — `git add rooms` · `git commit -m "Memories: edit caption and date, delete"`

## Walk through (chunk 5)

**Trace:** uploading three photos. `POST /places/<slug>/memories/new/` → `views.memory_create` → `get_own_place` → `MemoryUploadForm.is_valid()` → `MultipleImageField.clean` (Pillow opens each file; `validate_photo`) → for each file: `photo_taken_on` → `Memory.save()` → redirect → place page → the browser asks for `/memories/<pk>/photo/` three times → `views.memory_photo` → `get_own_memory` → the file.

**The builder runs:**
1. Uploads real photos taken in their room, including one screenshot (no camera date). Compares the dates shown with the phone's gallery.
2. Adds a caption and changes a date.
3. Copies one photo's address, opens it in a private window (sent to login), then as the second user (404).
4. Tries `http://127.0.0.1:8000/media/...` with the path seen in the admin and gets a 404.
5. If the phone has a HEIC photo, tries it and reads the message.
6. Double-clicks the upload button quickly and checks whether photos were added twice. If they were, tell the builder and record it as a known flaw; the fix (disabling the button after the first click) needs JavaScript and is not in this plan.

## Record (chunk 5)

Add "Photos" to the system map: the traced request, D2 and D3 as the builder's decisions with their reasons, the limits and where each is set, how the date is read, and the known limits (no thumbnails, location data kept, all-or-nothing batches, no HEIC).

## As built (chunk 5, 18 Nov 2026)

- **Decide.** D2 = a and D3 = a, the builder's answers on 17 Nov, both the recommended options. The calls above and the kit README's "Calls made here" have not been read out yet; they are listed for the builder at the end of the 18 Nov session.
- **Build.** The code came from `prebuilt/django/chunk5-parts` then `prebuilt/django/chunk5-rest/D2a-D3a`, applied with `kit.py apply --write`. Nothing was written by hand. Before applying, `kit.py verify --choice chunk5-D2a-D3a` on a fresh copy: all four lines `ok`, 195 tests.
- **After.** `makemigrations --check` reports no changes; no migration was needed. 195 tests pass in the project (the plan says 156 for its own list; the kit adds tests the plan did not name, listed in `prebuilt/django/chunk5-rest/README.md`, and the tests sit in four files by topic instead of one `test_memories.py`).
- **Real check.** A scratch copy of the app with its own database, run with `runserver`: 14 of 14 HTTP checks passed, plus a 404 for a stored photo's real `/media/...` path. Details in `docs/system-map.md`, piece 7. The photos were small Pillow-made JPEGs; real phone photos and a browser look are for the walk-through.
- **Recorded** as piece 7 in `docs/system-map.md` (piece 6 is the Colab notebook).

---

# Chunk 6: Runs from a fresh clone

**Ends with:** someone who has only the repository can install the app, run its tests and start it by following the README.

## Decide

**Builder's decisions:** none in this chunk. The open question in `CLAUDE.md` (are `CLAUDE.md` and `docs/` pushed to GitHub?) must be settled before any push, and pushing is not part of this plan. Remind the builder that it is still open.

**Claude's calls:** the README describes only what was run and seen to work. It lists what is not built yet. The AI section is a short, honest pointer; it is written properly with the AI work.

## Task 13: README and the clean-copy check

**Files:**
- Create: `README.md`
- Modify: `requirements.txt` (only if the check below finds it wrong)

**Interfaces:**
- Consumes: everything committed in chunks 1 to 5. This task needs those commits to exist; if the builder has not allowed commits, ask now.

- [ ] **Step 1: Write `README.md`** with these sections, in this order: what Memory Room is (two sentences); what works today (sign-up and login; places; room video upload; photos with captions; privacy between users) and what does not exist yet (the 3D room, automatic pinning, deployment); what you need (Python 3.14, git); set-up (the five commands below, for PowerShell, with the macOS/Linux form of the two interpreter paths); how to run; how to run the tests; where things are (the file map from this plan, trimmed); settings (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and that a key file is made automatically when the first is unset); AI (one paragraph: the reconstruction model is not connected to the app yet).

```powershell
git clone <repository address>
cd memory-room
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

- [ ] **Step 2: Prove it on a clean copy.** Clone the local repository into a new empty folder in the session's scratch directory and run the README's commands there exactly as written, then the tests.

```powershell
git clone "C:\Users\revaa\AI Projects\memory-room" "<scratch>\clean-copy"
cd "<scratch>\clean-copy"
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test
.venv\Scripts\python.exe manage.py check
```

Expected: every migration applies, 156 tests pass (adjust for D2, D3), `check` reports no issues, and a `.secret_key` file appears in the clean copy. If anything fails, the README or the repository is wrong: fix it, commit, and repeat from a new clean copy.

- [ ] **Step 3: Check what is in git.** In the real project: `git ls-files`. Expected: no `.venv`, `media/`, `db.sqlite3`, `.secret_key`, `.env`, `.idea/`, and (until the builder decides) no `docs/` or `CLAUDE.md`.

- [ ] **Step 4: Commit point** — `git add README.md requirements.txt` · `git commit -m "README: set-up, run and test instructions"`

## Walk through (chunk 6)

**The builder runs:** the README from top to bottom in a second clean copy, themselves, without Claude typing. Anything they had to guess is a README bug.

## Record (chunk 6)

Add "Running and reproducing" to the system map. In `CLAUDE.md`, mark the Django foundation done and set the next step: the plan for the Colab run and the 3D viewer page (spec §7, row 2), which starts with its own decisions (the points-file format, and how a points file gets attached to a scan).

---

# After this plan

Not built here, in the order the spec gives them. Each starts with its own Decide step.

1. **The Colab run and the 3D viewer page** (spec §7, 20 points). Open decisions waiting there: the format of the points file; how the file reaches a scan (the admin, or an upload page); whether a small sample points file is kept in the repository (note that `.gitignore` in this plan excludes `*.bin`).
2. **Loading experiment pins.** The Pin table from chunk 2 is ready for positions from the photo experiment, if it happens.
3. **Scope page and roadmap** (30 points). Needs the builder's P2-A2 submission.
4. **GitHub push** (10 points). Needs the builder's decision on `docs/` and `CLAUDE.md`.
5. **For the final submission, not the first draft:** a JSON API and a data feature (search, export), both required by Part 2 of the class brief.
