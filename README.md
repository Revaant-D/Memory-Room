# Memory Room

Film a room once on your phone. It becomes a 3D room you can turn and zoom around, and the photos you took in that room show up where they were taken.

A Django web app for INFO 490, Project 2, by Revaant Daga. **This is the first draft (18 Nov 2026).** The write-up for the draft (product scope, AI plan and evidence, progress and roadmap) is [`FIRST_DRAFT.md`](FIRST_DRAFT.md).

## What works today, and what doesn't yet

**Works, in the app:**

- Sign up, log in, log out.
- Places: create, rename, delete. Each user sees only their own; another user's address gives "page not found".
- Room videos: upload an MP4 or MOV (up to 500 MB) to a place; delete it.
- Photos: add up to 50 at once (JPEG, PNG or WebP, up to 20 MB each). The date is read from inside each photo. Add a caption, change the date, delete. Only the owner can open a photo file.
- The 3D room: once a scan's room is built and imported (see [AI](#ai)), "View the room in 3D" on the place's page opens it as coloured dots you can turn and zoom, with placed photos as dots; tap one to see the photo. Only the owner can open it.
- The admin site at `/admin/` shows every table.

**Works, outside the app:** a Google Colab notebook (`ai/build_room_colab.ipynb`) that turns a room video into a 3D room with the MapAnything model, and a command that brings the result into the app. See [AI](#ai) below.

**Not built yet:** the AI started from inside the app; photos placed in the room by the app (pins can only be added in the admin for now); placing a photo by hand; versions of a place; search; deployment. The roadmap is in `FIRST_DRAFT.md` §3.

## What you need

- Python 3.14
- git

Nothing else: the database is SQLite (a file), and uploads are stored on disk in `media/`.

## Set up

**Windows (PowerShell):**

```powershell
git clone https://github.com/Revaant-D/Memory-Room.git
cd Memory-Room
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
```

**macOS or Linux:**

```bash
git clone https://github.com/Revaant-D/Memory-Room.git
cd Memory-Room
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
```

The commands call the environment's Python by its path, so nothing needs activating. On macOS and Linux, use `.venv/bin/python` wherever this file says `.venv\Scripts\python.exe`.

Optional, to use the admin site: `.venv\Scripts\python.exe manage.py createsuperuser`.

## Run it

```powershell
.venv\Scripts\python.exe manage.py runserver
```

Then open http://127.0.0.1:8000/ and:

1. Sign up.
2. Create a place (for example "First flat").
3. On the place's page, add a room video, then add several photos at once.
4. Open a photo to give it a caption or change its date.

## Run the tests

```powershell
.venv\Scripts\python.exe manage.py test
```

229 tests, all passing on 18 Nov 2026. They use a temporary database and a temporary upload folder, so they never touch your own data.

The AI code has its own tests, which need numpy and OpenCV and run outside this environment. `ai/README.md` says how.

## Settings

All optional. Nothing needs setting to run on your own computer.

| Environment variable | What it does | If it is not set |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | The key Django signs logins and forms with | A random key is made on first run and saved in `.secret_key`, which git ignores |
| `DJANGO_DEBUG` | `1` shows detailed error pages; anything else turns them off | On (`1`). A deployed site must set `0` |
| `DJANGO_ALLOWED_HOSTS` | The host names the site answers to, separated by commas | Only this computer (`localhost`, `127.0.0.1`) while debug is on |

## AI

The 3D room is built by **MapAnything** (Meta and Carnegie Mellon, Apache-2.0 weights `facebook/map-anything-apache`) in a Google Colab notebook on a free GPU, outside the app, for this draft. The model choice, its input and output, and how it will connect to Django are in `FIRST_DRAFT.md` §2.

From a room video to the 3D page:

1. Film the room ([`docs/filming-guide.md`](docs/filming-guide.md)) and upload the video to a place in the app. It becomes a scan; its number is the "Id" column in the admin site's Scans list.
2. Run the notebook in Colab ([`ai/README.md`](ai/README.md)). It writes a room folder and a zip to Google Drive.
3. Download the zip (keep it outside the project folder: it shows the inside of the room), then:

   ```powershell
   .venv\Scripts\python.exe manage.py import_room <scan number> <path to the room zip or folder>
   ```

   The command checks the room and refuses anything it cannot trust, with the reason: a failed run, a damaged points file, the wrong weights, or a made-up room (from the code's stand-in model) unless `--made-up` is given, in which case every page labels it "MADE-UP ROOM".
4. Open the place's page and choose "View the room in 3D".

To try the page without a GPU, make the made-up demo room with the AI code (`python -m roompipe demo --out <folder>`, run from `ai/`; it needs numpy, see `ai/README.md`) and import it with `--made-up`.

## Where things are

```
Memory-Room/
├─ README.md            this file
├─ FIRST_DRAFT.md       the first-draft write-up
├─ manage.py            Django's command-line entry point
├─ requirements.txt     the exact library versions
├─ config/              settings and the top of the address map
├─ accounts/            the user, sign-up, login, logout
├─ rooms/               places, room videos (scans), photos (memories), pins
│  ├─ models.py         the four tables and their rules
│  ├─ access.py         the owner checks every page goes through
│  ├─ validators.py     the checks on uploaded videos and photos
│  ├─ roomfolder.py     reads and checks a room built in Colab
│  ├─ management/commands/import_room.py   attaches a built room to a scan
│  ├─ views.py, urls.py, forms.py, templates/rooms/
│  └─ tests/
├─ templates/           pages shared by the whole site (the frame, errors)
├─ static/css/site.css  the one stylesheet
├─ static/viewer/       the 3D viewer, and three.js 0.170.0 (MIT) in vendor/
├─ ai/                  the Colab notebook and the AI code it loads (not imported by Django)
├─ prebuilt/            code built ahead of time; what the app uses has been copied out of it
└─ docs/                design, plans, system map, product record, filming guide, research
```

**Documents:**

- `docs/system-map.md`: what each built piece does, how a request flows through it, and why each decision was made.
- `docs/features.md`: the product record: what is built, the AI features, what is planned, decisions, open questions.
- `docs/design/2026-11-16-first-draft.md`: the first-draft design; §6 is the data model.
- `docs/plans/`: the build plans.
- `docs/reference/`: the class brief (condensed) and the research behind the idea.

Made when the app runs, never in git: `.venv/`, `db.sqlite3`, `.secret_key`, `media/`.
