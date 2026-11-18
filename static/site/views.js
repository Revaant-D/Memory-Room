// Camera positions shared by more than one page. All in the room's DRAWN
// frame (room3d.js turns the room so its walls line up with the screen).

// How much further back the camera stands on a tall, narrow (phone) screen,
// so the whole room still fits.
export function distanceFor(w, h) {
  return Math.max(1, Math.min(1.55, 0.72 / (w / h)));
}

// The small turning model on the places page. The room page starts here when
// you come from that page, then dives in, so the move reads as one.
export function placesView(room, w, h) {
  // Its box is often taller than wide on a phone, and the model sits at an
  // angle, so it needs more room than the other views.
  const [cx, cy] = room.box.centre, far = Math.max(1, Math.min(1.9, 1.15 / (w / h)));
  return room.view([cx + 6 * far, cy - 11 * far, 0.6 + 8.4 * far], [cx, cy, 0.6], 21);
}

// The room from above at an angle, its walls cut low so the inside shows.
export function overviewView(room, w, h) {
  const [cx, cy] = room.box.centre, far = distanceFor(w, h);
  return room.view([cx + 0.6 * far, cy - 5 * far, 0.2 + 6.6 * far], [cx, cy, 0.2], 44);
}

// Straight down, for placing a photo by tapping the floor.
export function aboveView(room, w, h) {
  const [cx, cy] = room.box.centre, far = distanceFor(w, h);
  return room.view([cx, cy - 0.01, 9.5 * far], [cx, cy, 0], 38);
}
