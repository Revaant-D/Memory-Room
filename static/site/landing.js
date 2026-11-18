// The front page: the public room's dots gather into the room, which then turns
// slowly. Under reduced motion it simply appears and stays still (M9).
import { loadPoints } from "../viewer/loaders.js";
import { createRoom } from "../viewer/room3d.js";

const holder = document.getElementById("landing-room");
try {
  const { positions, colors } = await loadPoints(holder.dataset.points, "ply");
  // The public copy keeps about a third of the points, so each dot is drawn a little larger.
  const room = createRoom(holder, { positions, colors, pointSize: 0.032 });
  const [cx, cy] = room.box.centre;
  room.uniforms.cut.value = 1.85; // the ceiling off, so you look in

  let first = true;
  room.onResize((w, h) => {
    // Further back on a tall phone screen, so the whole room fits; beside the words on a wide one.
    // On a phone the words fill the lower half, so the room stands back and sits
    // in the upper half (aiming below the room lifts it on screen).
    const narrow = w <= 800;
    const far = narrow ? Math.max(1, Math.min(2.2, 1.2 / (w / h))) : 1;
    const aim = narrow ? -0.9 : 0.7;
    room.shift.value = narrow ? 0 : 0.17;
    const view = room.view([cx + 3.4 * far, cy - 6.6 * far, aim + 4.3 * far], [cx, cy, aim], 40);
    room.flyTo(view, 0, { orbit: true }).then(() => room.spin(0.5));
    if (first && !room.reduceMotion) {
      first = false;
      room.uniforms.spread.value = 1;
      room.animate("spread", room.uniforms.spread, 0, 3200);
    }
  });
  room.controls.enableZoom = false;
} catch {
  holder.remove(); // the words alone, on the field
}
