# Memory Room: first-draft design

**Written 16 Nov 2026. Covers the work up to Wednesday 18 Nov 2026, 11:59 PM.** The builder approved the target, the order and the calls in §5 in conversation on 16 Nov. The builder decided the data model in §6 on 16 Nov. The build plan for the Django foundation is `docs/plans/2026-11-16-django-foundation.md`.

## 1. Intent

Hand in the class first draft (P2-A3) with a working Django foundation and real evidence that the AI part is feasible.

The builder's wider aim, in their words: to build it "in a structured way ... where I am in the loop for decisions on how it works so that I know the entire system properly and the different components in it by the time it is done."

The product: film a room once on a phone; it becomes a 3D room you can turn; photos taken in that room are pinned where they were taken. The full idea is in the research repo (see `CLAUDE.md`).

## 2. Goals, non-goals, anti-goals

**Goals for 18 Nov**
- Everything the first-draft rubric asks for (`docs/reference/assignment.md`).
- The first real run of the reconstruction model on a video of the builder's own room.
- The builder can explain each piece that exists.

**Non-goals for 18 Nov** (all planned for later)
- Django starting GPU jobs itself.
- Automatic pinning of photos inside the app.
- Deployment.
- Search, timeline, export and share links.
- Voice notes.
- More than one version of a room, and the time slider. This was already a stretch item.

**Anti-goals**
- An app that works but that the builder cannot explain.
- Claiming a result that was not actually obtained. The class forbids it.
- Spending the three days on the uncertain AI run and missing the Django foundation, which carries 40 of the 100 first-draft points.

## 3. Constraints

- About 24 hours of the builder's time: 8 hours a day on 16, 17 and 18 Nov.
- One builder, with Claude Code writing the code this week.
- The builder's phone is a Galaxy S23 FE. The only GPU is a free Colab one, which is not always available.
- The reconstruction code has never run on a real video.
- Model weights: `facebook/map-anything-apache` only (Apache 2.0).
- No keys or model weights in git.

## 4. Approaches considered

| Approach | What it is | Trade-off |
| --- | --- | --- |
| **A. Foundation plus experiment (chosen)** | A complete Django foundation. The AI runs as a Colab experiment on a real room, and its real output is shown in a 3D viewer page inside the app | The AI is not wired into Django yet. That is allowed for the first draft |
| B. Thin end-to-end | Wire Django to a rented GPU job and the viewer by Wednesday | GPU hosting setup and the first real model run would land in the same three days. If either slips, the foundation is at risk |
| C. Django only | The foundation, with the AI as a written plan | Safest, but the biggest unknown stays untested, and there is no evidence of experimentation |

Claude recommended A and the builder agreed on 16 Nov.

## 5. What was decided

**By the builder**
- The Wednesday target and the order of work in §7.
- A basic working prototype matters more than a finished product at this stage.

**Claude's calls, which the builder accepted on 16 Nov**
- Claude writes the code until the first draft is in; the builder makes the decisions.
- The app lives in its own repository, separate from the research repo, because the instructor grades repository organisation.
- SQLite for the database and local disk for uploaded files, for now.
- PyCharm is where the builder reads and runs the code.
- One main Claude Code session for the app. The builder's second account is spare capacity, or runs the Colab notebook work, which touches no Django files.

## 6. Data model

**Status, 16 Nov 2026: decided.** The builder chose the shape (a separate Pin model) and then approved the field list and rules below, which Claude proposed.

### The decision: where a pin lives

A pin's x, y, z only mean something inside one scan. Every reconstruction run has its own origin and direction, so the same numbers point to a different spot in a second scan of the same room. Three shapes were considered:

| | Shape | Trade-off |
| --- | --- | --- |
| A | Memory -> Place; x, y, z on the memory | Simplest. Correct only while a place has one scan |
| B | Memory -> Place, plus an optional link to the scan the pin was measured in | One extra column. One pin per photo |
| **C (chosen)** | A separate Pin model: memory, scan, x, y, z | An extra table. One photo can have a pin in every version of the room |

Claude recommended B. **The builder chose C on 16 Nov.** What C buys: a photo is a thing in a place, and a pin is a separate fact about where that photo sits in one particular scan. When versions arrive, nothing has to be reshaped.

### The models (Claude's proposal)

```
User    Django's built-in user

Place   owner -> User
        name
        slug          made from the name; unique per owner; used in the URL
        created

Scan    place -> Place
        video         the uploaded room video
        taken_on      the day it was filmed; defaults to the upload day
        status        uploaded / building / ready / failed
        points_file   empty until a room has been built
        created

Memory  place -> Place
        photo
        caption       optional
        taken_on      optional
        created

Pin     memory -> Memory
        scan -> Scan
        x, y, z       metres, in that scan's frame; floor at z = 0, z up
        placed_by     user / ai
        created
```

### Rules (Claude's calls)

- **A memory has at most one pin per scan.** The database enforces it.
- **A pin's memory and scan must belong to the same place.** Checked when a pin is saved.
- **No pin row means "not pinned".** There are no empty x, y, z fields and no "none" value for `placed_by`. The later "needs you" list is the memories in a place that have no pin in the scan being viewed.
- **Deleting:** a place takes its scans, memories and pins with it. A scan takes its pins; the photos stay. A memory takes its pins. Uploaded files are removed from disk with their rows.
- **A place can hold several scans** even though versions are a non-goal: a failed build can be re-filmed. Pages show the newest ready scan.
- **Slugs are unique per owner,** not across the site, so two users can each have a "dorm-room".
- **The video is kept for now.** The technical design deletes it after the room is built; that rule arrives when Django runs the build itself.
- Project name `config`, app name `rooms`, as in the technical design.

### Left out until the piece that needs it

- Pin: the direction the camera faced (`yaw_deg`) and the agreement between the two placement tries (`gap_m`). Both arrive with automatic placement.
- Scan: `n_points`, `room_box`, `to_first`, `error`. They arrive with the viewer and the build job.
- Anchor and Job models: with the GPU job.
- VoiceNote and ShareLink: non-goals in §2.

### What this means for the first draft

Pinning inside the app is a non-goal for 18 Nov, so no page creates pins yet. The Pin table will exist with its rules and tests, and stays empty unless Wednesday's photo experiment produces positions to load.

## 7. Work and order

Hours are Claude's estimates.

| First-draft part (points) | What gets built | Hours |
| --- | --- | --- |
| Django foundation (40) | Sign-up and login; places, scans and memories; upload a room video and photos; add captions; a page per place; each user sees only their own places | 7 |
| AI plan and evidence (20) | Run MapAnything on a real video of the builder's room in Colab; show that room as coloured points in a three.js viewer page inside the app; try placing about ten photos if time allows | 9 |
| Scope page (15) | One page, including what changed since P2-A2 | 1.5 |
| Roadmap (15) | The table from the brief | 0.5 |
| GitHub and README (10) | A clean repository that runs from a fresh clone | 2 |
| Buffer | | 4 |

- **Mon 16 Nov:** the Django foundation. The builder films the room.
- **Tue 17 Nov:** the Colab run and the viewer page.
- **Wed 18 Nov:** the photo experiment if time allows, the write-ups, and the push. Building stops by early evening.

## 8. Risks

- **The Colab run fails or no free GPU is available.** It is the first real run of that code. If it fails, the first draft reports what happened; a documented failed attempt is still evidence of experimentation. The viewer page can then be shown with a synthetic room, labelled as synthetic.
- **The existing code does not save colour.** `stage1.py` keeps points without colour. The model does return the input image per view (`img_no_norm`), so the notebook needs a small addition to export coloured points.
- **The scope page needs the P2-A2 submission,** which Claude has not seen.
- **Usage limits** on the builder's Claude plan over 8-hour days.

## 9. Left to the builder of each piece

- Page layout and styling.
- The Django project and app names.
- The format of the points file the viewer reads.
- Test coverage beyond the basics: the model rules, and that one user cannot open another user's place.

## 10. After the first draft

In order: Django starts the build-room job on a rented GPU; pins placed by hand in the viewer; automatic placement with a confidence check; search, timeline, export and sharing; evaluation; deployment; documentation and the video. Each gets its own decisions before it is built.
