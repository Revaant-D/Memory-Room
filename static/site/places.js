// Your places: each place with a built room is a small model of it, turning
// slowly on the field. The whole model is a link; dragging is off, so a tap
// always opens the place.
import { loadPoints } from "../viewer/loaders.js";
import { createRoom } from "../viewer/room3d.js";
import { placesView } from "./views.js";

for (const link of document.querySelectorAll(".model")) {
  const holder = link.querySelector(".model__room");
  link.addEventListener("click", () => {
    try { sessionStorage.setItem("memoryroom-dive", link.dataset.slug); } catch { /* private mode: no dive */ }
  });
  loadPoints(holder.dataset.points, "ply").then(({ positions, colors }) => {
    const room = createRoom(holder, { positions, colors, pointSize: 0.03 });
    room.uniforms.cut.value = 1.9; // the ceiling off, so the inside shows
    room.controls.enableRotate = false;
    room.controls.enableZoom = false;
    room.onResize((w, h) => room.flyTo(placesView(room, w, h), 0, { orbit: true }).then(() => room.spin(0.6)));
  }).catch(() => holder.classList.add("model__room--missing"));
}
