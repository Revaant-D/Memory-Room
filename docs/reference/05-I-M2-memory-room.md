# Memory Room (I-M2)

> Film a room once on any phone. It becomes a 3D room you can turn, and the photos you already took there pin themselves where you stood.

**Status (16 Nov 2026):** a new idea, written up the day after the five-idea comparison. It has **not been judged, debated or measured**. It grew out of the builder's own idea (Moments in 3D, I-M1) by moving it from people to places. A one-day phone test comes before any build. "Memory Room" is a working name.

This file is self-contained. You don't need any other file to understand the idea, what already exists, how it would be built, its risks and what to do next.

---

## 1. The idea in plain words

You're about to leave a room for good: a dorm room in May, the apartment you shared for two years, the house your parents are selling. You have hundreds of photos taken in it, scattered through your camera roll, and no way to see the room itself again.

With Memory Room:
1. You open a web page on your phone and film one slow walk around the room, 60–90 seconds.
2. A few minutes later the room appears in 3D. You can turn it, zoom in and look down into it like a dollhouse.
3. You pick photos from your camera roll that were taken in that room.
4. Each photo **pins itself where you were standing when you took it**. If the app isn't sure, it asks you to tap the spot and doesn't guess.
5. You tap a pin to open the photo, add a caption or a voice note, or jump to the exact view the photo was taken from.
6. You film the room again whenever it changes: empty on move-in day, lived in by winter, packed up in May. Each video becomes a new **version** of the same place. You drag through time to watch it change, and each photo shows in the version it belongs to. (This part was the builder's own addition on 16 Nov.)
7. You share the room by link. Later, the people you lived with can add their own photos to the same room.

The product isn't "a 3D scanner". The room is the **index**: it turns a pile of photos into a place you can go back into, at any point in its life.

## 2. Why it might work

- **Rooms hold still.** Moments in 3D needed sharp 3D of people from a few photos, and people move between shots. That was its documented failure case. A room doesn't move, so one phone video is the kind of input today's 3D models are built for.
- **The same model can place other photos.** MapAnything takes a set of photos and returns where each camera was. If a few frames from the room video go in together with one of your old photos, the old photo's position comes out in the same pass. Nothing has to be trained. **Whether this works for a photo taken months earlier, in different light, has not been measured** (§11).
- **The reconstruction code already exists in this repo** (`creating-idea/09-sprint/reconstruct_colab.ipynb`). So far it has run on synthetic rooms only.
- **A place changes, and the change is part of the memory.** Keeping versions shows how a room filled up and emptied out. It should also help the AI: an old photo can be matched against the version nearest its date, with the furniture as it was then. Lining two versions up is untested.
- **It has a fallback that keeps the product.** If automatic placement fails, you tap where you stood. The app still works, though it loses its most distinctive part.
- **No 3D faces.** People appear only inside ordinary photos, as in any photo app. Nothing rebuilds a person in 3D or runs face recognition, which is what raised the biometric-law question for Moments in 3D.
- **A deadline.** Move-out day is a reason to do it now and not "sometime".

## 3. Who it's for and when

| Who | The moment | Why them |
| --- | --- | --- |
| Students leaving a dorm room or shared apartment | The last week before move-out | Reachable on campus now; the room is gone for them afterwards; they have many photos taken in it |
| Friends leaving a shared place at graduation | Packing week | Several people hold photos of the same room, which suits a shared room |
| Families selling or clearing a home | Before the sale or clear-out | Strongest feeling, but harder to reach and outside the class window |

**Moment:** the days before leaving a place you won't be able to walk into again.

## 4. Evidence that people want this (honest version)

The evidence is thin. Nothing was gathered for this idea beyond two quick searches, and nobody has been interviewed.

| What was found | Source | How strong |
| --- | --- | --- |
| Almost three-quarters of phone photos are never looked at again; only 16% of people looked back at more than a quarter of their photos in a year | Popsa survey of 8,000 people, via a trade report (evidence note E-525) | Vendor survey, second-hand |
| "The camera roll has become a filing system rather than a memory system." | Popsa's chief executive, same report | Opinion from a company that sells photo books |
| People go back to photos when a feeling or a mention prompts them, not by browsing | Mixbook 2025 habits report (E-524) | Vendor survey |
| A Dutch tech site ran "Make a 3D scan of your house, so you never forget what it looked like" (Aug 2026) | bright.nl headline; body not read | One article |
| A homeowner scanned his self-built home before selling it, partly to keep a record | Matterport blog | Vendor case study |
| The pull of 3D memories was found only among headset owners | Moments in 3D research (E-521 to E-534) | Desk research |

**Against:** consumer 3D-photo products closed for low use (Lytro, Seene, Microsoft Photosynth), and no source shows people paying to keep a room. Whether students would bother in the last week of term is unknown.

## 5. Competitors and prior art (quick check)

Eight quick searches on 16 Nov 2026, plus what the Moments in 3D research had already found. This is far lighter than the 18 to 27 searches each compared idea received, and app-store pages were read from search snippets only.

| Product | What it does | Overlap | What it lacks |
| --- | --- | --- | --- |
| **GausNote** (iPad, free) | Opens a 3D scan and lets you pin text notes, voice memos and photos on its surfaces by hand; sends the annotated scan as one file | **High:** pins in a 3D scan already ship | iPad only (iPadOS 26.2 or later); every pin placed by hand; appears to need a scan made in another app; the other person needs the app. Source is the developer's own listing |
| **RecallSpace** (iPhone, free) | Maps a room with the phone's AR and pins notes, photos and calendar events to objects, as a "memory palace" study aid | Medium | Pins show only while you stand in the room; iPhone only; described as in active development |
| **Matterport tags** | Labels pinned to spots in a 3D tour that carry text, photos, video and links | Medium | Placed by hand; built for property and construction |
| **Microsoft Photosynth** | Pooled many photos of a place into a 3D "synth" you could move through, each photo shown where it was taken | High in spirit | Public places, needed many photos; apps retired 2015, service shut 6 Feb 2017 |
| **Multi Splat** (Captures Studio, free) and **TimeSplat 4D** (Split View Studio) | Line up several 3D captures of the same place and step through them in a browser, as a timeline or with a draggable seam | Medium: versions of a place already ship | Tools for people who already have finished 3D files; no phone capture and no photos tied to a version. Matterport and Nira offer side-by-side comparison for building sites |
| **Scaniverse, Polycam, Splatt** | Free or cheap 3D scans of rooms and objects | Medium on the scan | A bare scan; no photos or notes placed in it were found in their listings |
| **Memoom** (web) | Made-up 3D rooms where you pin photos, notes and quotes | Low | Not a scan of your real room; found as a portfolio listing only |
| **Apple Spatial Scenes** | Turns one photo into a 3D-looking scene | Low | One photo at a time, not a place |
| **Photo placement research** | Patents and papers on working out where a photo was taken inside a 3D model; Reconstruct places site photos in a building model for construction | The technique exists | No consumer app was found that does this for your own room |

**What's left that nobody was found doing:** (a) placing the photos you already have, automatically; (b) doing it in a browser on any phone, Android included; (c) versions of the place over time, with each photo kept in the version it belongs to; (d) a room that several people add to.

**How novel is that?** Partly. Pinning by hand already ships (GausNote), and stepping through versions of a place already ships as a separate tool (Multi Splat, TimeSplat 4D). So the claim rests on (a) and on joining the pieces for someone who has only a phone. GausNote or Scaniverse could add it: it's a feature, not a barrier. An earlier version of this pitch said scan apps hold no memories at all; the GausNote find makes that wrong.

## 6. How it's built

| Component | Input → output | Tech |
| --- | --- | --- |
| Capture page | Phone video → upload | Django form; the phone's own camera through a file input |
| Frame picker | Video → about 60 sharp frames | OpenCV on the server (Apache 2.0) |
| Build-room job | Frames → coloured 3D points and the camera position of every frame | **MapAnything, `facebook/map-anything-apache` weights (Apache 2.0)** on a GPU rented by the minute (Modal) |
| Room model | Points → levelled, thinned point set, plus about 20 "anchor" frames with their positions | NumPy |
| Place-photo job | Anchors + up to about 10 of your photos → position and direction of each photo | MapAnything again, then a fit that lines the anchors up with their stored positions (Umeyama fit, NumPy) |
| Confidence check | Two tries with different anchors → do they agree? | NumPy; pin it if they agree within about 0.7 m and 30°, otherwise ask the user `[assumption: thresholds set in the test]` |
| Version line-up | A later scan of the same place → lined up with the earlier one | A few frames from both scans go through MapAnything together, then the same fit. If it fails, versions show side by side |
| Viewer | Points + pins → a 3D room in the browser, with a time slider across versions | three.js (MIT) |
| Web app | Accounts, places, memories, search, share links, JSON API | Django |

**Why coloured points first, not a splat.** MapAnything already outputs coloured points, so the room can be shown with no extra training step. A sharper Gaussian-splat view (gsplat, Apache 2.0) is a later upgrade.

**What is stored:** the 3D points, about 20 anchor frames, your photos and notes. The video is deleted after the room is built. Rooms are private unless you share a link.

**Not yet known:** MapAnything has never run on a real Galaxy S23 FE video in this repo; how the point view looks on a real room; whether a months-old photo lands in the right place; whether two versions filmed months apart line up.

## 7. How it fits the class project (INFO 490 Project 2, final push 8 Dec 2026)

| Part | Points | What this app gives |
| --- | --- | --- |
| 1. Scope and experience | 10 | Three features: film a room into 3D; photos pin themselves; search, timeline and share. One clear path from video to pinned room |
| 2. Django | 25 | Models: User, Place, Scan, Memory, VoiceNote, ShareLink. Login and per-user rooms. Upload and edit forms. JSON API for pins. Search, timeline and export as the data feature |
| 3. AI | 25 | Two AI steps inside the workflow: build the room, place each photo. A confidence check decides between pinning and asking. Handles bad video, photos from another room and GPU failures |
| 4. Evaluation | 15 | Metrics: distance from the true spot, share placed without help, wrong confident pins, time per job. Five tests; failures are expected and are part of the write-up |
| 5. Deployment and cost | 15 | Django on a free host calling a rented GPU. Natural cost comparison: GPU per job (about $0.80 an hour while running) against an always-on GPU (about $576 a month at the same rate) |
| 6. Documentation | 10 | README, AI notes, no keys or model weights in the repo |

The class says you don't need to prove there are no competitors, only why a user might prefer yours. Section 5 covers that.

## 8. Hours and a three-week plan

About **50 hours** of the builder's time with Claude Code writing most of the code (range 35 to 75). This is a first estimate, not a scope card.

| Piece | Hours |
| --- | --- |
| One-day phone test (first real run, ten photos) | 6 |
| Django base: accounts, places, uploads, pages | 5 |
| Search, timeline, JSON API, export | 3 |
| GPU jobs: build room, place photos | 8 |
| 3D viewer with pins | 8 |
| Confidence check and tap-to-place | 6 |
| Phone debugging (video formats, uploads) | 3 |
| Evaluation: 5 tests, 2 failures, 1 fix | 4 |
| Deployment | 3 |
| README, AI notes, cost and scaling write-up | 3 |
| Three-minute video | 2 |
| **Total** | **51** |

**Stretch, not in the 51:** a second version of the room and the time slider, about 7 hours. Do it only if the phone test passes early. For the class video, two versions can be made a day apart by rearranging the room.

| Week | Dates | Work | Hours |
| --- | --- | --- | --- |
| 1 | 16–22 Nov | Phone test and decision; Django base; search, timeline, API | 14 |
| 2 | 23–29 Nov (Thanksgiving) | GPU jobs; 3D viewer with pins | 16 |
| 3 | 30 Nov–6 Dec | Confidence check and tap-to-place; phone debugging; evaluation; deployment | 16 |
| 4 | 7–8 Dec | README and AI notes; video; final push | 5 |

The class first draft was due 9 Nov. No Django project exists in this repo yet.

## 9. Where it stands next to the five compared ideas

| Idea | Novelty | Feasibility | Demand | Commercial | Balanced |
| --- | --- | --- | --- | --- | --- |
| One Video, One Tape | 3.0 | 3.5 | 3.0 | 3.0 | 3.12 |
| Coverage Certificate | 3.5 | 3.0 | 3.5 | 2.5 | 3.10 |
| Order-Safe Takeoff | 2.5 | 3.5 | 3.0 | 2.5 | 2.85 |
| Skip-the-Tape Check | 3.0 | 3.0 | 3.0 | 2.0 | 2.71 |
| Moments in 3D | 2.5 | 2.5 | 2.5 | 2.0 | 2.36 |
| **Memory Room** | not judged | not judged | not judged | not judged | — |

Memory Room has no scores because no judge has seen it. My expectation, which is not a score: it wouldn't beat One Video, One Tape on that rubric, because its demand evidence is thinner and comparable apps are free. The reasons to pick it are different: it's the idea the builder wants to build, it suits the class rubric, and it avoids what sank Moments in 3D (people moving, 3D faces).

## 10. Risks (a first pass; no pre-mortem has been run)

| # | Cause | Likelihood × impact | Fix |
| --- | --- | --- | --- |
| 1 | **Old photos don't land in the right place** (different light, moved furniture, close-ups with little room in view) | 3 × 5 = 15 | Find out on day one. The confidence check asks the user when unsure; tap-to-place keeps the app working |
| 2 | **The 3D room looks rough** as coloured points (holes, noise, thin walls) | 4 × 3 = 12 | More frames; a dollhouse view from above hides holes; splat view later |
| 3 | **People look once and never return** (what closed Photosynth, Lytro and Seene) | 4 × 4 = 16 | Tie it to move-out; shared rooms so friends add photos; a short fly-through video to post |
| 4 | **Privacy**: home interiors and photos of friends on a server | 2 × 4 = 8 | Private by default; share by link only; one-tap delete; no face recognition |
| 5 | **Pipeline and ops overrun** (GPU setup, cold starts, phone video formats) | 3 × 3 = 9 | Start from the existing notebook; pick frames on the server; pinned container image |
| 6 | **GausNote or Scaniverse adds automatic placement** | 2 × 3 = 6 | None; move faster on Android, versions and the shared room |
| 7 | **Two versions of a room don't line up**, so the walls jump when you drag through time | 3 × 2 = 6 | Line them up from frames of both scans run together; if that fails, show versions side by side |

Risk 3 is the one with no test inside the class window.

## 11. What to do next

**The one-day test** (free Colab, existing notebook plus a small addition that prints each photo's camera position; that addition isn't written yet):
1. Film your room: one slow walk, 60–90 seconds, 1–2 m from the walls, floor in view.
2. Choose ten photos taken in that room. Take five today from spots you mark on the floor, so the true position is known. Take the other five from your camera roll, as old and as different in light as you have.
3. Run the notebook on the video frames and the ten photos together.
4. Compare where each photo landed with where you stood.

**Pass line:** at least 8 of 10 land within arm's length (0.7 m) of the true spot and face the right wall.

| Result | Do this |
| --- | --- |
| 8 or more of 10 | Build it with automatic pins as the headline |
| 5 to 7 of 10 | Build it; the app will ask more often, so lead with the 3D room |
| Fewer than 5 | Pins by hand only (weaker: that's GausNote in a browser), or return to One Video, One Tape |

Then, before much building: show the mock screens to five students who are moving out this year. A fair bar is three of five saying they would film their room and naming photos they would pin.

## 12. Open questions

- [ ] Does a months-old photo land in the right place (the test)?
- [ ] Do two versions of a room, filmed months apart, line up well enough that the walls don't jump?
- [ ] How does the coloured-point room look on a real video?
- [ ] How many frames fit on a free GPU, and how long does a room take?
- [ ] Does GausNote make its own scans, and does it run on iPhone?
- [ ] Would anyone open the room again after the first week?
- [ ] Does the class allow a rented GPU as the deployment, or must everything run on the web host?

## 13. Constraints it must respect

No model training · no dependence on another organisation · running cost inside the free GPU credit · only the builder's phone (Galaxy S23 FE) and laptop plus a GPU by the minute · licences that allow commercial use · private by default · Django, three weeks, final push 8 Dec 2026.

## Sources

- Closest products: apps.apple.com/app/gausnote/id6784539731 · apps.apple.com/ca/app/recallspace/id6774547087 · recallspaceapp.netlify.app · matterport.com/blog/multimedia-mattertagtm-posts-embed-video-audio-and-more-your-3d-spaces · contra.com/p/qXg2AvPb-memoom-3-d-memory-rooms-web-app · en.wikipedia.org/wiki/Photosynth
- Versions of a place: radiancefields.com/captures-studio-releases-multi-splat-for-aligning-comparing-and-replaying-gaussian-splat-captures-in-the-browser · radiancefields.com/platforms/split-view-studio · matterport.com/blog/compare-two-3d-models · help.nira.app/hc/en-us/articles/47711927824667-Timeline-Compare-3D-Models-and-2D-Maps
- Photo placement: image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9741121 (photograph localization in a 3D model) · blog.reconstructinc.com/reconstruct-inc/get-instant-access-to-photos-in-context-e1a2ccda2ad9
- Wanting to keep a place: bright.nl/plusplus/2120375/maak-een-3d-scan-van-je-huis-zo-vergeet-je-nooit-hoe-het-eruit-zag.html · matterport.com/en-gb/blog/matterport-scans-preserve-beloved-self-built-home-forever
- Model: github.com/facebookresearch/map-anything · arXiv 2509.13414
- Run files: `creating-idea/10-compare/05-decision/REPORT.md` (the five-idea comparison), `creating-idea/10-compare/01-new-idea/` (Moments in 3D research: P-I-M0-deep.md, evidence E-501 to E-551), `creating-idea/10-compare/02-refresh/S-I2-03.md` (GPU cost figures), `creating-idea/03-tech-radar/C-03-mapanything.md`
