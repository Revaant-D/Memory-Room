// The room page (rooms/room.html): the room in 3D, its photos as pink dots,
// and a strip of every photo. Opening a photo, placing one and stepping
// between photos all happen here, without loading another page.
//
// Rules from the bug review of 18 Nov (docs/design/2026-11-18-dollhouse-site.md):
//   M1/M8  every flight and every delayed step checks it is still the current one
//   M4/S7  an open photo is in the address (?photo=<id>); Back closes it
//   M5     the strip starts at the left when it overflows (CSS)
//   M6     anything not showing is `hidden`, so Tab can't reach it
//   M7     dots don't take taps while placing
//   M11    captions are set as text, never as HTML
//   S1     a tapped spot is sent in the scan's own frame (room.floorAt gives that)
//   S5     a tap outside the room's footprint is refused

import { loadPoints } from "../viewer/loaders.js";
import { createRoom } from "../viewer/room3d.js";
import { aboveView, distanceFor, overviewView, placesView } from "./views.js";

const $ = (id) => document.getElementById(id);
const data = JSON.parse($("room-data").textContent);
const photos = data.photos;
const placed = () => photos.filter((p) => p.pin);
const label = (p) => p.caption || "Photo with no caption";

let room = null;
let state = "loading"; // "overview" | "photo" | "placing" | "saving"
let current = null; // the open photo
let moving = null; // the photo being placed
let views = null;
let pushed = false; // did opening a photo add a history step? Then Back closes it.
const pinEls = new Map();
const stemEls = new Map(); // a thin line from each dot down to the floor: where it stands

// --- what shows when ----------------------------------------------------------

function only(...ids) {
  for (const id of ["strip", "caption", "card", "photo-nav", "placing", "ghost"]) $(id).hidden = !ids.includes(id);
  $("pins").hidden = !ids.includes("pins");
  // While placing, the dots are seen but take no taps (M7).
  $("pins").inert = state === "placing" || state === "saving";
  document.body.classList.toggle("placing-now", ids.includes("placing"));
}

function setBack(toRoom) {
  const back = $("back");
  back.textContent = toRoom ? "Room" : back.dataset.label;
}

// --- the strip and the dots --------------------------------------------------------

function thumb(p) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = p.pin ? "thumb" : "thumb thumb--waiting";
  button.dataset.id = p.id;
  const img = document.createElement("img");
  img.src = p.src;
  img.alt = p.pin ? label(p) : `${label(p)}, not placed yet`;
  img.loading = "lazy";
  button.append(img);
  if (!p.pin) button.title = "Not placed yet: tap to place it";
  button.addEventListener("click", () => (p.pin ? openPhoto(p) : startPlacing(p)));
  button.addEventListener("mouseenter", () => hot(p, true));
  button.addEventListener("mouseleave", () => hot(p, false));
  return button;
}

function renderStrip() {
  const strip = $("strip");
  strip.replaceChildren(...placed().map(thumb), ...photos.filter((p) => !p.pin).map(thumb));
  const add = document.createElement("a");
  add.className = "thumb thumb--add";
  add.href = strip.dataset.add;
  add.setAttribute("aria-label", "Add photos");
  add.innerHTML = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M8 3v10M3 8h10"/></svg>';
  strip.append(add);
}

function renderPins(dropped = null) {
  const holder = $("pins");
  holder.replaceChildren();
  pinEls.clear();
  stemEls.clear();
  for (const p of placed()) {
    const stem = document.createElement("span");
    stem.className = "pin-stem";
    holder.append(stem);
    stemEls.set(p.id, stem);
    const button = document.createElement("button");
    button.type = "button";
    button.className = p.id === dropped ? "pin pin--dropped" : "pin";
    button.setAttribute("aria-label", label(p));
    button.addEventListener("click", () => openPhoto(p));
    button.addEventListener("mouseenter", () => hot(p, true));
    button.addEventListener("mouseleave", () => hot(p, false));
    holder.append(button);
    pinEls.set(p.id, button);
  }
  room?.redraw();
}

function hot(p, on) {
  pinEls.get(p.id)?.classList.toggle("pin--hot", on);
  document.querySelector(`.thumb[data-id="${p.id}"]`)?.classList.toggle("thumb--hot", on);
}

function placeDots() {
  for (const p of placed()) {
    const el = pinEls.get(p.id);
    const at = room.project(p.pin.x, p.pin.y, p.pin.z);
    const floor = room.project(p.pin.x, p.pin.y, 0);
    el.hidden = !at.visible;
    el.style.transform = `translate(${at.x}px, ${at.y}px)`;
    const stem = stemEls.get(p.id);
    stem.hidden = !at.visible || !floor.visible;
    const length = Math.hypot(floor.x - at.x, floor.y - at.y);
    const angle = Math.atan2(floor.y - at.y, floor.x - at.x);
    stem.style.width = `${length}px`;
    stem.style.transform = `translate(${at.x}px, ${at.y}px) rotate(${angle}rad)`;
  }
}

// --- the room from above (the place's own view) -----------------------------------

async function overview(ms = 1400) {
  state = "overview";
  current = null;
  moving = null;
  setBack(false);
  only();
  room.hidePhotos();
  room.animate("tint", room.uniforms.tintAmount, 0, 400);
  room.animate("near", room.uniforms.near, 0, 300);
  room.animate("cut", room.uniforms.cut, 1.3, 900);
  const arrived = await room.flyTo(views.overview, ms, { orbit: true });
  if (!arrived || state !== "overview") return; // something newer took over (M1, M8)
  room.controls.enableZoom = true;
  only("strip", "pins");
}

// --- a photo, opened where it was taken -----------------------------------------------

async function openPhoto(p, { push = true } = {}) {
  if (!p?.pin) return;
  const from = state;
  state = "photo";
  current = p;
  if (push) {
    const address = `${location.pathname}?photo=${p.id}`;
    // The first photo opened adds a history step, so Back closes it (M4, S7);
    // stepping between photos replaces it, so Back still returns to the room.
    if (from === "photo") history.replaceState({ photo: p.id }, "", address);
    else { history.pushState({ photo: p.id }, "", address); pushed = true; }
  }
  setBack(true);
  only();
  document.querySelectorAll(".pin--hot").forEach((el) => el.classList.remove("pin--hot"));
  room.hidePhotos(200);
  const lined = Boolean(p.pin.camera);
  room.animate("cut", room.uniforms.cut, lined ? 99 : 2.2, 500);
  room.animate("tint", room.uniforms.tintAmount, 0, 300);
  room.animate("near", room.uniforms.near, 0, 200);
  const view = lined ? room.photoView(p.pin, 1.3) : room.spotView(p.pin, views.far);
  const arrived = await room.flyTo(view, from === "photo" ? 1300 : 1900, { arc: lined && from !== "photo" ? 1.2 : 0 });
  if (!arrived || state !== "photo" || current !== p) return; // M1, M8

  $("caption-text").textContent = label(p); // text, never HTML (M11)
  $("caption-when").textContent = [p.date, p.pin.placedBy === "user" ? "Placed by you" : ""].filter(Boolean).join(". ");
  $("edit").href = p.edit;
  room.animate("tint", room.uniforms.tintAmount, lined ? 0.55 : 0.3, 700);
  if (lined) {
    room.animate("near", room.uniforms.near, 0.7, 700);
    const img = new Image();
    img.onload = () => {
      if (current === p && state === "photo") room.showPhoto(p.pin, p.src, img.naturalWidth / img.naturalHeight, true, 700);
    };
    img.src = p.src;
    only("caption", "photo-nav");
  } else {
    $("card-img").src = p.src;
    $("card-img").alt = label(p);
    only("caption", "photo-nav", "card", "pins");
    pinEls.get(p.id)?.classList.add("pin--hot");
  }
  $("photo-nav").querySelectorAll("button").forEach((b) => (b.disabled = placed().length < 2));
}

function step(direction) {
  if (state !== "photo") return;
  const list = placed();
  const i = list.indexOf(current);
  if (list.length > 1) openPhoto(list[(i + direction + list.length) % list.length]);
}

function closePhoto() {
  if (pushed) { history.back(); return; } // popstate brings the room back
  // Arrived on the photo's own address: there is no step to go back to, so
  // swap the address for the room's instead of leaving the page.
  history.replaceState(null, "", location.pathname);
  overview();
}

window.addEventListener("popstate", () => {
  if (!room) return;
  const id = Number(new URLSearchParams(location.search).get("photo"));
  const p = photos.find((q) => q.id === id && q.pin);
  if (p) openPhoto(p, { push: false });
  else { pushed = false; if (state !== "overview") overview(); }
});

// --- placing a photo by tapping the floor ------------------------------------------------

async function startPlacing(p) {
  if (location.search.includes("photo=")) history.replaceState(null, "", location.pathname);
  pushed = false;
  state = "placing";
  moving = p;
  current = null;
  setBack(false);
  only("pins");
  $("placing-note").textContent = "";
  $("ghost").querySelector("img").src = p.src;
  room.hidePhotos(200);
  room.animate("tint", room.uniforms.tintAmount, 0, 400);
  room.animate("near", room.uniforms.near, 0, 300);
  room.animate("cut", room.uniforms.cut, 1.6, 800);
  const arrived = await room.flyTo(views.above, 1400);
  if (!arrived || state !== "placing" || moving !== p) return;
  only("pins", "placing", "ghost");
}

async function placeAt(clientX, clientY) {
  if (state !== "placing") return;
  const spot = room.floorAt(clientX, clientY); // in the scan's own frame (S1)
  const { low, high } = data.box || { low: [-Infinity, -Infinity], high: [Infinity, Infinity] };
  if (!spot || !room.onFloor(spot[0], spot[1]) ||
      spot[0] < low[0] || spot[0] > high[0] || spot[1] < low[1] || spot[1] > high[1]) {
    $("placing-note").textContent = "That’s outside the room. Tap the floor where you stood.";
    return;
  }
  const p = moving;
  state = "saving";
  $("placing-note").textContent = "Saving";
  const body = new FormData();
  body.append("memory", p.id);
  body.append("x", spot[0].toFixed(2)); // centimetres are plenty for a finger
  body.append("y", spot[1].toFixed(2));
  let answer = null;
  try {
    const response = await fetch(data.pinUrl, { method: "POST", body, headers: { "X-CSRFToken": $("csrf").value } });
    answer = await response.json().catch(() => ({ error: `The server answered ${response.status}.` }));
    if (!response.ok && !answer.error) answer.error = `The server answered ${response.status}.`;
  } catch {
    answer = { error: "Couldn’t reach the server. Check the connection and tap again." };
  }
  if (state !== "saving" || moving !== p) return;
  if (answer.error) {
    state = "placing";
    $("placing-note").textContent = answer.error;
    return;
  }
  p.pin = answer.pin;
  renderStrip();
  renderPins(p.id); // the dot drops in where you tapped
  state = "placing"; // still from above, so you see it land
  only("pins");
  setTimeout(() => { if (moving === p && state === "placing") overview(); }, 900);
}

// --- the menu -----------------------------------------------------------------------------

function setMenu(open) {
  $("menu").hidden = !open;
  $("menu-button").setAttribute("aria-expanded", String(open));
  if (open) $("menu").querySelector("a")?.focus();
}
$("menu-button").addEventListener("click", (event) => {
  event.stopPropagation();
  setMenu($("menu").hidden);
});
document.addEventListener("click", (event) => {
  if (!$("menu").hidden && !event.target.closest("#menu")) setMenu(false);
});

// --- controls -----------------------------------------------------------------------------

$("back").addEventListener("click", (event) => {
  if (state === "photo") { event.preventDefault(); closePhoto(); }
});
$("previous").addEventListener("click", () => step(-1));
$("next").addEventListener("click", () => step(1));
$("move").addEventListener("click", () => current && startPlacing(current));
$("placing-cancel").addEventListener("click", () => overview());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (!$("menu").hidden) { setMenu(false); $("menu-button").focus(); }
    else if (state === "photo") closePhoto();
    else if (state === "placing") overview();
  }
  if (event.key === "ArrowRight") step(1);
  if (event.key === "ArrowLeft") step(-1);
});

// A tap on the room (not a drag) while placing.
let pressed = null;
$("room").addEventListener("pointerdown", (e) => (pressed = { x: e.clientX, y: e.clientY }));
$("room").addEventListener("pointerup", (e) => {
  if (pressed && Math.hypot(e.clientX - pressed.x, e.clientY - pressed.y) < 6) placeAt(e.clientX, e.clientY);
  pressed = null;
});
$("room").addEventListener("pointermove", (e) => {
  if (state === "placing") $("ghost").style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
});

// --- start ----------------------------------------------------------------------------------

try {
  const { positions, colors } = await loadPoints(data.points, "ply");
  room = createRoom($("room"), { positions, colors });
  $("status").hidden = true;
  room.onFrame(placeDots);
  room.onResize((w, h) => {
    views = { overview: overviewView(room, w, h), above: aboveView(room, w, h), places: placesView(room, w, h), far: distanceFor(w, h) * 1.25 };
    if (state === "overview") room.flyTo(views.overview, 0, { orbit: true }); // a turned phone (M12)
    if (state === "placing") room.flyTo(views.above, 0);
  });
  renderStrip();
  renderPins();

  // Coming from your places: start where the model was, then dive in.
  let dive = false;
  try {
    dive = sessionStorage.getItem("memoryroom-dive") === location.pathname.split("/")[2];
    sessionStorage.removeItem("memoryroom-dive");
  } catch { /* storage blocked: no dive */ }
  room.uniforms.cut.value = 1.9;
  if (dive) room.jump(views.places);
  else room.jump(views.overview);

  const open = photos.find((p) => p.id === data.open && p.pin);
  if (open) {
    history.replaceState({ photo: open.id }, "", location.href);
    openPhoto(open, { push: false });
  } else {
    overview(dive ? 1700 : 0);
  }
} catch (error) {
  $("status").textContent = `The room couldn’t be shown: ${error.message}`;
  $("strip").hidden = false;
  renderStrip();
}
