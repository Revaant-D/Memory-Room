# How to film a room for Memory Room

Written 17 Nov 2026 for the first real run, on a Galaxy S23 FE. The 3D room is built from about 60 frames picked from your video, so the video has to show every part of the room, sharply, from several positions. Later this becomes the in-app "how to film" guide (`docs/features.md`).

Filming takes about 15 minutes, including setting up and the placement-test photos.

## 1. Set up the room (5 minutes)

- Turn on every light. Close curtains on any window that has direct sun on it.
- Leave the room as it is: it is the room you want to keep. Just make sure the floor is visible in most places.
- Nobody walks through, and pets are out. Anything that moves during filming becomes noise.
- **For the placement test (recommended):** write 1 to 5 in large marker on five sheets of plain white paper. Lay them flat on open floor, spread through the room, at spots where you would naturally stand to take a photo (the doorway, by the desk, by the bed...). Leave them there while you film. They show up as white patches in the room seen from above, so you can see whether each photo landed where you stood.

## 2. Camera settings (Samsung Camera app)

| Setting | Use | Why |
| --- | --- | --- |
| Mode | **Video** | |
| Resolution | **FHD (1920 × 1080), 30 frames a second**. Tap the resolution label at the top of the screen | 4K makes a file three times larger for no gain: the model works at 518 pixels |
| Lens | **1×**. Not 0.5× (ultra-wide), no zoom | The ultra-wide lens bends straight lines |
| HDR10+ video | **Off**, if you see it (Camera settings → Advanced video options) | HDR video can come out washed out when the frames are read |
| Super Steady | **Off** | It crops the picture and changes the view while you film |
| Ordinary stabilisation | On is fine | |

## 3. Film (60 to 90 seconds)

**Hold the phone upright (portrait)** at chest height and **tilt it down a little**, so the floor fills about the bottom third of the screen the whole time. Don't turn the phone sideways at any point.

Portrait, because most photos you will want to place are portrait, and the model crops every image in a batch to one shape. A portrait room keeps those photos whole.

1. Start at the doorway, looking into the room.
2. **Walk slowly along the walls, about 1 to 1.5 m in from them, with the camera pointing across the room** at the far side. You are walking a loop around the room while looking at its middle and the opposite walls.
3. **Slow down at corners.** Walk around the corner while turning; don't stand and spin.
4. Finish back at the doorway, and **keep going a few steps past where you started**, so the end of the video overlaps the beginning.

About one slow step a second. A typical bedroom takes 60 to 90 seconds.

**Don't:**
- Spin in place. Turning without moving gives the model no depth.
- Pan fast or swing the phone.
- Fill the screen with a blank wall up close.
- Point at a mirror or a bright window for more than a moment.
- Move anything between filming and taking the placement photos.

## 4. Check it (1 minute)

Play it back. It should be **sharp**, **upright**, **show the whole room** including the floor, and be **60 to 90 seconds**. At FHD it will be roughly 130 to 200 MB. If a stretch is blurred or you missed a corner, film again; it is quicker than finding out in Colab.

## 5. Photos for the placement test (optional, about 5 minutes)

- **Five new ones:** stand on each numbered sheet in turn (1 to 5, in order) and take one ordinary photo of whatever you'd naturally photograph from there. Portrait, 1×. The order tells you which photo belongs to which sheet.
- **Five old ones** of this room from your gallery, as different as you have: one with people in it, one at night, one close-up, one from months ago.

Ten photos is one batch for the model. HEIC photos work, but JPEG is safest.

## 6. Get the files to Colab

In the **Google Drive app** on the phone, on Wi-Fi:

1. My Drive → **New folder** `MemoryRoom`.
2. Inside it: **+ → Upload** → the room video.
3. Inside it, a folder `photos` → upload the ten photos.
4. Wait until Drive shows every upload as finished.

Keep the video on the phone too: it also goes into the app as the room's scan.

Then follow "Running the notebook" in `ai/README.md`.
