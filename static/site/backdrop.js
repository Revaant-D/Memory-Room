// The room, faint and still, behind a form page (base.html). It is drawn once
// and never again: no animation, no battery (bug review, M10).
import { loadPoints } from "../viewer/loaders.js";
import { createRoom } from "../viewer/room3d.js";

const holder = document.getElementById("backdrop");
try {
  const { positions, colors } = await loadPoints(holder.dataset.points, "ply");
  const room = createRoom(holder, { positions, colors, still: true });
  const [cx, cy] = room.box.centre;
  room.uniforms.cut.value = 1.9; // no ceiling, so the inside shows
  room.onResize((w, h) => {
    const far = Math.max(1, Math.min(1.55, 0.72 / (w / h)));
    room.jump(room.view([cx + 6 * far, cy - 11 * far, 0.6 + 8.4 * far], [cx, cy, 0.6], 30));
  });
} catch {
  holder.remove(); // the plain field is fine
}
