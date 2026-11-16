# Memory Room (I-M2): technical feasibility check

> Can the technical design actually build the idea? A skeptical read, plus an answer to "is Gaussian splatting the only way to turn an indoor scan into 3D?"

**Status (16 Nov 2026):** a desk review. Nothing was run. It reads the design and checks it against the model's current documentation. It does not replace the one-day phone test.

**Verdict:** the idea is buildable as a class project, but nothing in it has run on real data yet. The 3D room is low-risk. "Photos pin themselves" is plausible but unproven, and weaker than the write-up suggests for the photos people care about most.

This file sits beside the documents it reviews:

| File | What it is |
| --- | --- |
| `05-I-M2-memory-room.md` / `.pdf` | The idea write-up |
| `T5-I-M2-memory-room-technical.pdf` | The technical design being reviewed |
| `T0-master-phone-to-3d-techniques.pdf` | The catalogue of phone-to-3D techniques |

---

## 1. What was checked, and how

- **The two technical PDFs** were read through the scripts that generate them (`Final Ideas/pdf-src/tech_i_m2.py` and `master.py`), because no PDF renderer was installed. The content is the same.
- **The existing code**: `creating-idea/09-sprint/stage1.py` and its README, plus the tech-radar card `C-03-mapanything.md`.
- **MapAnything's current README and image-loading code** on GitHub, fetched on 16 Nov 2026. Section 2 lists what they say.

Anything not in that list is general knowledge and is marked as such where it matters.

## 2. Facts confirmed from the MapAnything repository

| Question | What the repository says | What it means here |
| --- | --- | --- |
| Does the call in `stage1.py` match the real one? | Yes. Same arguments; bf16 "falls back to fp16 if bf16 not supported" | The reconstruction code should run with small fixes at most |
| Is there a colour output? | Yes: `img_no_norm`, the input image per view | The design marked this "to confirm". It is confirmed |
| What happens to images of different shapes? | The loader takes the average aspect ratio of the whole set, picks one shape from a fixed table, and forces every image to it. Long side is 518 pixels | Landscape video frames mixed with portrait photos get cropped. See risk 2c |
| Can some views carry known camera poses while others are image-only? | Yes, inputs are set per view. If any view has a pose, the first view must have one. Depth needs intrinsics too | A possible better way to place photos. See section 5 |
| How much GPU memory for how many frames? | "Up to 2000 views on 140 GB" in memory-efficient mode. No guidance for 16 GB or 24 GB | Whether 60 frames fit on a free Colab GPU is still unknown |
| How do the two weight sets differ? | Apache 2.0 and CC BY-NC. "The only difference is the training data composition and resulting license terms." The non-commercial set is recommended "for the best performance" | The Apache set the design uses is the weaker one. No numbers are given |
| Does it support placing a new photo in an existing reconstruction? | Not mentioned | Placement is an off-label use of the model |
| Is there a route to Gaussian splats? | Yes: a script exports to COLMAP format, then gsplat (`gsplat==1.3.0` recommended) | The "later upgrade" in the design has a documented path |

## 3. What holds up

- **Video to 3D room.** This is what MapAnything is built for, and the call in the repo matches the current documentation.
- **Web app, viewer and tap-to-place.** Ordinary Django and three.js work. Tapping the floor to get room coordinates is a few lines.
- **The fallback.** If automatic placement fails, pinning by hand still gives a working app that meets the class requirements.

## 4. Where to be skeptical

### Risk 1: nothing has run on real data
The reconstruction code has been tested on synthetic rooms only, and the MapAnything call has never executed. The placement code is a sketch. Every number in the design (job times, costs, point counts, thresholds) is a guess.

### Risk 2: automatic placement is the weakest part
The mechanism is sound in principle: run a few stored frames together with the new photo and read off the photo's camera position. But the model's documentation doesn't describe this use, and three specific problems stand out.

- **2a. People photos.** The photos worth pinning are mostly selfies, friends and close-ups, where little of the room is visible. The test in §11 of the idea write-up uses five photos taken today from marked spots, which is the easy case.
- **2b. Move-out timing.** The product's moment is the last week before leaving. A half-packed room with bare walls is when the room looks least like the old photos.
- **2c. Mixed shapes.** The image loader forces every image to one shape (section 2). A portrait photo run with landscape video frames loses much of its content. The fix is easy (group photos by orientation, or rotate the anchors to match), but the design doesn't cover it.

### Risk 3: the two-try confidence check is not independent
Both tries use the same model and the same photo, with half the anchors each. A wrong answer tends to repeat, so agreement between the two is weaker evidence than it looks. The check will catch some failures, but not confident wrong ones. A stronger check would count matching image features between the photo and the stored frame it claims to be near (general knowledge; not designed here).

### Risk 4: the room will look rough
- The model works at 518 pixels on the long side, and the design thins points to 2 cm. That gives a fuzzy dotted room, not a photoreal one.
- The Apache weights are the weaker set (section 2).
- Seen from outside, a closed room shows its ceiling and the backs of its walls. The dollhouse view needs the ceiling hidden, which the design doesn't mention.

For a product about memories, the look matters more than it did for the measuring ideas.

### Risk 5: plumbing is under-budgeted
- A 60–90 second phone video is roughly 100–200 MB (an estimate). It goes through a Django form on a free host, then on to the GPU worker.
- Three hours for phone debugging is optimistic.
- Whether 60 frames fit on a free 16 GB GPU is undocumented (section 2).

## 5. One possible improvement

The design places a photo by running the model fresh and then lining the result up with the stored room (the Umeyama fit). MapAnything accepts known camera poses for some views and none for others. Feeding the stored anchor frames with their known poses, and the new photos as images only, might make the model answer directly in the room's own frame and remove the fit. This is untested for this use.

## 6. Is Gaussian splatting the only way?

No, and the design doesn't use it: it shows coloured points and lists splats as a later upgrade.

| Way | What you get | Cost | Fit here |
| --- | --- | --- | --- |
| Coloured points from a feed-forward model (the plan) | A dotted room | Seconds, no training | Start here |
| Mesh, by fusing the model's depth maps | Solid surfaces and a natural dollhouse view | CPU minutes, no new model | Best first upgrade if the points look poor |
| Gaussian splat | The closest to photoreal | GPU training per room; needs accurate camera poses; a heavier viewer | Later. The repository documents an export to gsplat |
| Classic photogrammetry | A textured mesh | Slow; fails on blank walls | Poor for dorm rooms |
| Neural radiance field (NeRF) | Photoreal, but slow in a browser | GPU training per room | Largely replaced by splats for viewing |
| Depth sensor (LiDAR iPhone, ARCore depth) | Clean geometry | Needs a native app; LiDAR isn't the builder's phone | Out of scope |
| Show the real video frames at their positions | The actual pixels | No extra compute | A cheap complement to any of the above |

The costs in this table are general knowledge, not measurements.

## 7. What to change before building

1. **Run the one-day test before any web code**, as the idea write-up already says.
2. **Make the test harder.** Use real camera-roll photos: people shots, selfies and portrait orientation, not only photos of the room taken today.
3. **Count wrong confident pins**, not only how many photos land. That number is what the two-try check is supposed to keep low.
4. **Look at the point room on the phone** before committing to it as the product's look. If it is too rough, try the mesh before the splat.
5. **Write down GPU memory and time** for the first real run, since neither is documented.

## 8. Still unknown after this check

- [ ] Does a real camera-roll photo, with people in it, land in the right place?
- [ ] How often does the two-try check pass a wrong answer?
- [ ] How does the coloured-point room look on a real video?
- [ ] Do 60 frames fit on a free 16 GB GPU, and how long does a room take?
- [ ] How much worse are the Apache weights than the non-commercial ones on a real room?
- [ ] Does giving the anchors their known poses (section 5) work for placing photos?

## Sources

- MapAnything README: raw.githubusercontent.com/facebookresearch/map-anything/main/README.md (fetched 16 Nov 2026)
- MapAnything image loader: raw.githubusercontent.com/facebookresearch/map-anything/main/mapanything/utils/image.py (fetched 16 Nov 2026)
- Design sources in this repo: `Final Ideas/pdf-src/tech_i_m2.py`, `Final Ideas/pdf-src/master.py`, `creating-idea/09-sprint/stage1.py`, `creating-idea/09-sprint/README.md`, `creating-idea/03-tech-radar/C-03-mapanything.md`
