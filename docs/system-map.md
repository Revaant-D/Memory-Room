# Memory Room: system map

What has been built, where it lives, how a request moves through it, and why each decision was made. One section per piece. Each section is added when its piece is built, so anything described here exists and has been run.

**Last updated:** 16 Nov 2026, after chunk 1 of `docs/plans/2026-11-16-django-foundation.md`.

## What exists today

A Django project that runs, with accounts: a person can sign up, log out and log in. Places, room videos, photos and the 3D room are not built yet.

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

There are 50 tests. All 50 passed on 16 Nov 2026.

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
├─ accounts/                  the user, sign-up, login, logout
└─ rooms/                     today: the home page. Later: places, scans, memories, pins
```

Made when the app runs and never put in git: `.venv/` (the libraries), `db.sqlite3` (the database), `.secret_key`, and later `media/` (uploads).

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

## Before deployment

Things that are right for a laptop and wrong for a public site. Nothing here is a fault today.

- Cookies are not marked secure-only, and plain HTTP is not redirected to HTTPS. `manage.py check --deploy` lists four warnings, all of this kind.
- With debug off, Django's development server stops serving the stylesheet. A real host serves static files itself.
- SQLite and local disk are to be replaced (Postgres and a file bucket in the technical design).
