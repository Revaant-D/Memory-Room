// The 3D room: coloured points you can turn, with a pin for each photo.
//
// One function, createRoomViewer(container, options), draws the room into a
// page element and returns a small object for changing it afterwards. It
// knows nothing about Django or about where the data came from: it is given
// plain arrays and plain objects.
//
//   const viewer = createRoomViewer(document.querySelector("#room"), {
//     positions,                 // Float32Array, x y z per point (metres; floor z = 0, z up)
//     colors,                    // Uint8Array, r g b per point (0 to 255)
//     box: { low: [x, y, z], high: [x, y, z] },   // the room's extent
//     pins: [{ id, x, y, z, label, placedBy }],   // placedBy: "ai" or "user"
//     onPinSelect(pin) {},       // a pin was tapped (or null: the tap missed every pin)
//   });
//
//   viewer.setPins(pins)             replace the pins
//   viewer.selectPin(id)             mark one pin as chosen (null for none)
//   viewer.setView("inside"|"above") stand in the room, or look down into it
//   viewer.startPlacing(callback)    the next tap on the floor calls callback({x, y, z})
//   viewer.cancelPlacing()
//   viewer.dispose()                 remove the viewer and free the graphics memory
//
// Needs three.js (import name "three") and its OrbitControls add-on; the page
// says where they are with an import map. See demo.html.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

// Point and pin colours are drawn exactly as given, with no colour
// conversion. This is a setting for the whole page, not only this viewer.
THREE.ColorManagement.enabled = false;

const PIN_COLORS = { ai: 0xe4572e, user: 0x2f6fdd, other: 0x777777 };
const PIN_RADIUS = 0.05; // metres
const EYE_HEIGHT = 1.5; // metres: the height given to a pin placed by tapping the floor
const TAP_SLOP = 6; // pixels a finger may drift and still count as a tap, not a drag

export function createRoomViewer(container, options) {
  // pointSize: the width of each dot in metres. A little more than the gap
  // between points (the room is thinned to one point per 2 cm) so that a wall
  // reads as a surface, not as scattered dots.
  const { positions, colors, pins = [], onPinSelect = () => {}, pointSize = 0.03 } = options;
  const count = positions.length / 3;
  const low = new THREE.Vector3(...options.box.low);
  const high = new THREE.Vector3(...options.box.high);
  const centre = low.clone().add(high).multiplyScalar(0.5);
  const size = high.clone().sub(low);

  // --- the canvas -----------------------------------------------------------
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch (error) {
    container.textContent = "This browser cannot draw 3D here, so the room cannot be shown.";
    throw error;
  }
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace; // see ColorManagement above
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); // sharp, but not wasteful
  renderer.localClippingEnabled = true; // lets the "above" view cut the ceiling away
  renderer.domElement.style.display = "block";
  renderer.domElement.style.touchAction = "none"; // drags turn the room; they do not scroll the page
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x15151a);

  const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 200);
  camera.up.set(0, 0, 1); // in the room frame z is up (three.js assumes y)

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.addEventListener("change", draw);

  // --- the room: one dot per point -----------------------------------------
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  // `true`: the bytes 0..255 are read as 0..1 by the graphics card.
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3, true));
  const cutAbove = new THREE.Plane(new THREE.Vector3(0, 0, -1), 1e6); // keeps what is below a height
  const material = new THREE.PointsMaterial({
    size: pointSize, // metres: dots shrink with distance, like real things
    vertexColors: true,
    clippingPlanes: [cutAbove],
  });
  const cloud = new THREE.Points(geometry, material);
  scene.add(cloud);

  // --- the pins -------------------------------------------------------------
  const pinGroup = new THREE.Group();
  scene.add(pinGroup);
  const ball = new THREE.SphereGeometry(PIN_RADIUS, 20, 14);
  let pinMeshes = []; // one sphere per pin; mesh.userData.pin is the pin's own object
  let selectedId = null;

  function clearPins() {
    for (const child of [...pinGroup.children]) {
      pinGroup.remove(child);
      if (child.geometry !== ball) child.geometry.dispose();
      child.material.dispose();
    }
    pinMeshes = [];
  }

  function setPins(newPins) {
    clearPins();
    for (const pin of newPins) {
      if (![pin.x, pin.y, pin.z].every(Number.isFinite)) continue; // nothing to draw
      const color = PIN_COLORS[pin.placedBy] ?? PIN_COLORS.other;
      const mesh = new THREE.Mesh(ball, new THREE.MeshBasicMaterial({ color }));
      mesh.position.set(pin.x, pin.y, pin.z);
      mesh.userData.pin = pin;
      pinGroup.add(mesh);
      pinMeshes.push(mesh);
      // A thin line down to the floor. In a cloud of dots it is hard to judge
      // how far away a floating ball is; the line shows where it stands.
      const stem = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(pin.x, pin.y, 0),
          new THREE.Vector3(pin.x, pin.y, pin.z),
        ]),
        new THREE.LineBasicMaterial({ color }),
      );
      pinGroup.add(stem);
    }
    selectPin(selectedId);
  }

  function selectPin(id) {
    selectedId = id;
    for (const mesh of pinMeshes) {
      mesh.scale.setScalar(mesh.userData.pin.id === id ? 1.4 : 1);
    }
    draw();
  }

  // --- where the camera stands ---------------------------------------------
  let view = "inside";

  function setView(name) {
    view = name === "above" ? "above" : "inside";
    const reach = Math.max(size.x, size.y);
    if (view === "above") {
      // Look down into the room from outside one long wall, with the ceiling
      // and the top of the walls cut away so the inside can be seen.
      cutAbove.constant = low.z + size.z * 0.75;
      controls.target.set(centre.x, centre.y, low.z + size.z * 0.3);
      camera.position.set(centre.x, centre.y - reach * 0.9, low.z + size.z * 0.75 + reach * 0.9);
      controls.minDistance = 0.5;
      controls.maxDistance = reach * 4;
    } else {
      // Stand near the middle of the room at eye height and look across it.
      cutAbove.constant = 1e6;
      controls.target.set(centre.x, centre.y, low.z + Math.min(EYE_HEIGHT, size.z * 0.6));
      camera.position.set(centre.x - size.x * 0.3, centre.y - size.y * 0.3, low.z + Math.min(EYE_HEIGHT + 0.2, size.z * 0.7));
      controls.minDistance = 0.2;
      controls.maxDistance = reach * 4;
    }
    controls.update();
    draw();
  }

  // --- taps: choosing a pin, or placing one ---------------------------------
  const raycaster = new THREE.Raycaster();
  const floor = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0); // z = 0
  let placing = null; // the callback waiting for a tap on the floor
  let pressedAt = null;

  function rayFrom(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    const point = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(point, camera);
    return raycaster.ray;
  }

  function onPointerDown(event) {
    pressedAt = { x: event.clientX, y: event.clientY };
  }

  function onPointerUp(event) {
    if (!pressedAt) return;
    const moved = Math.hypot(event.clientX - pressedAt.x, event.clientY - pressedAt.y);
    pressedAt = null;
    if (moved > TAP_SLOP) return; // that was a drag to turn the room

    const ray = rayFrom(event);
    if (placing) {
      const hit = ray.intersectPlane(floor, new THREE.Vector3());
      if (!hit) return; // the tap pointed at the sky; keep waiting
      const callback = placing;
      cancelPlacing();
      // Centimetres are plenty for a spot chosen with a finger.
      const round = (value) => Math.round(value * 100) / 100;
      callback({ x: round(hit.x), y: round(hit.y), z: EYE_HEIGHT });
      return;
    }
    const hits = raycaster.intersectObjects(pinMeshes, false);
    onPinSelect(hits.length ? hits[0].object.userData.pin : null);
  }

  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);

  function startPlacing(callback) {
    placing = callback;
    renderer.domElement.style.cursor = "crosshair";
  }

  function cancelPlacing() {
    placing = null;
    renderer.domElement.style.cursor = "";
  }

  // --- drawing --------------------------------------------------------------
  // The picture is redrawn only when something changes (a drag, new pins, a
  // new size), not sixty times a second. A still room uses no battery.
  let queued = false;
  function draw() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      renderer.render(scene, camera);
    });
  }

  function fit() {
    const width = Math.max(1, container.clientWidth);
    const height = Math.max(1, container.clientHeight);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    draw();
  }
  const watcher = new ResizeObserver(fit);
  watcher.observe(container);

  fit();
  setPins(pins);
  setView(options.view || "inside");

  return {
    setPins,
    selectPin,
    setView,
    startPlacing,
    cancelPlacing,
    // Facts about what is on screen. Used by the page, and by checks.
    info() {
      return { points: count, pins: pinMeshes.length, view, placing: placing !== null, selected: selectedId };
    },
    // Where a pin is on the page, in the same coordinates a click event uses,
    // or null if it is behind the camera. Lets a page put a label on a pin.
    pinScreenPosition(id) {
      const mesh = pinMeshes.find((m) => m.userData.pin.id === id);
      if (!mesh) return null;
      camera.updateMatrixWorld();
      const spot = mesh.position.clone().project(camera);
      if (spot.z < -1 || spot.z > 1) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      return {
        x: rect.left + ((spot.x + 1) / 2) * rect.width,
        y: rect.top + ((1 - spot.y) / 2) * rect.height,
      };
    },
    dispose() {
      watcher.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      controls.dispose();
      clearPins();
      ball.dispose();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
