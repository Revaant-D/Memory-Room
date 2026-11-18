// The 3D room, Dollhouse look (18 Nov 2026). Replaces roomviewer.js.
//
//   const room = createRoom(container, { positions, colors });
//
// positions: Float32Array, x y z per point, in the scan's own frame (metres,
// floor z = 0, z up). colors: Uint8Array, r g b per point.
//
// The room is drawn turned about z so its walls line up with the screen
// (roomgeom.wallAngle). That turn is for drawing only: every function below
// takes and gives points in the SCAN's frame, so what the page saves (a
// tapped spot) is in the same frame as the stored room and its pins (S1).
//
// It draws only while something moves (a flight, a turn, a drag): a still
// room uses no battery (M10). With { still: true } it draws once and stops.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import { footprint, turnXY, unturnXY, wallAngle } from "./roomgeom.js";

THREE.ColorManagement.enabled = false; // colours are drawn exactly as stored

export const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const VERT = /* glsl */ `
  attribute vec3 color;
  attribute vec3 scatter;
  uniform float size, scale, spread, near;
  varying vec3 vColor;
  varying float vZ, vNear;
  void main() {
    vColor = color;
    vZ = position.z;
    vec4 mv = modelViewMatrix * vec4(position + scatter * spread, 1.0);
    vNear = -mv.z - near;
    gl_PointSize = clamp(size * scale / -mv.z, 1.0, mix(64.0, 5.0, min(spread * 4.0, 1.0)));
    gl_Position = projectionMatrix * mv;
  }`;

const FRAG = /* glsl */ `
  uniform vec3 tint;
  uniform float tintAmount, cut;
  varying vec3 vColor;
  varying float vZ, vNear;
  void main() {
    if (vZ > cut || vNear < 0.0) discard;
    gl_FragColor = vec4(mix(vColor, tint, tintAmount), 1.0);
  }`;

export function createRoom(container, { positions, colors, still = false, pointSize = 0.024, tint = 0x3e4752 }) {
  const count = positions.length / 3;
  const inRoom = footprint(positions); // built in the scan's frame, before turning
  const turn = wallAngle(positions);

  // Turned copy for drawing, and the box of what is drawn.
  const drawn = new Float32Array(positions.length);
  const low = [Infinity, Infinity, Infinity], high = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < count; i++) {
    const [x, y] = turnXY(positions[i * 3], positions[i * 3 + 1], turn);
    drawn[i * 3] = x; drawn[i * 3 + 1] = y; drawn[i * 3 + 2] = positions[i * 3 + 2];
    for (let k = 0; k < 3; k++) {
      low[k] = Math.min(low[k], drawn[i * 3 + k]);
      high[k] = Math.max(high[k], drawn[i * 3 + k]);
    }
  }
  const box = { low, high, centre: low.map((v, k) => (v + high[k]) / 2), size: low.map((v, k) => high[k] - v) };
  const toDrawn = (x, y, z) => new THREE.Vector3(...turnXY(x, y, turn), z);
  const R = new THREE.Matrix4().makeRotationZ(turn);
  const FLIP = new THREE.Matrix4().makeScale(1, -1, -1); // OpenCV camera axes to three.js

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: still });
  } catch (error) {
    container.textContent = "This browser can't draw 3D, so the room can't be shown.";
    throw error;
  }
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.style.cssText = "display:block;width:100%;height:100%;touch-action:none";
  container.append(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.03, 300);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.enabled = false;
  controls.addEventListener("change", wake);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(drawn, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3, true));
  const scatter = new Float32Array(count * 3);
  for (let i = 0; i < scatter.length; i++) scatter[i] = (Math.random() - 0.5) * 4;
  geometry.setAttribute("scatter", new THREE.BufferAttribute(scatter, 3));
  const uniforms = {
    size: { value: pointSize }, scale: { value: 1 }, spread: { value: 0 }, near: { value: 0 },
    tint: { value: new THREE.Color(tint) }, tintAmount: { value: 0 }, cut: { value: 99 },
  };
  scene.add(new THREE.Points(geometry, new THREE.ShaderMaterial({ uniforms, vertexShader: VERT, fragmentShader: FRAG })));

  // --- photos lined up with the room (pins that know their camera) ---------
  const loader = new THREE.TextureLoader();
  const planes = new Map(); // memory id -> mesh
  function cameraMatrix(pin) {
    const r = pin.camera.rotation;
    const m = new THREE.Matrix4().set(
      r[0][0], r[0][1], r[0][2], pin.x,
      r[1][0], r[1][1], r[1][2], pin.y,
      r[2][0], r[2][1], r[2][2], pin.z,
      0, 0, 0, 1,
    );
    return R.clone().multiply(m).multiply(FLIP);
  }
  function plane(pin, src, aspect) {
    if (planes.has(pin.memory)) return planes.get(pin.memory);
    const d = 0.5, h = 2 * d * Math.tan(THREE.MathUtils.degToRad(pin.camera.vfov) / 2);
    const texture = loader.load(src, wake);
    texture.colorSpace = THREE.NoColorSpace;
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(h * aspect, h),
      new THREE.MeshBasicMaterial({ map: texture, transparent: true, opacity: 0, depthTest: false }),
    );
    mesh.renderOrder = 10;
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(cameraMatrix(pin)).multiply(new THREE.Matrix4().makeTranslation(0, 0, -d));
    scene.add(mesh);
    planes.set(pin.memory, mesh);
    return mesh;
  }

  // --- motion: tweens, flights, drawing only while something moves -----------
  const tweens = new Map();
  // Slides the picture sideways by a share of its width, without moving the camera:
  // the front page puts the room beside its words this way.
  const shift = { value: 0 };
  let flight = 0; // the number of the latest flight (M1)
  let running = false;
  const listeners = [];

  function tween(key, ms, step) {
    return new Promise((resolve) => {
      tweens.get(key)?.done(false);
      if (reduceMotion || ms <= 0) { step(1); wake(); resolve(true); return; }
      tweens.set(key, { start: performance.now(), ms, step, done: resolve });
      wake();
    });
  }

  function frame(now) {
    for (const [key, t] of tweens) {
      const p = Math.min(1, Math.max(0, (now - t.start) / t.ms));
      t.step(p);
      if (p >= 1) { tweens.delete(key); t.done(true); }
    }
    const moved = controls.enabled ? controls.update() : false;
    uniforms.scale.value = renderer.domElement.height / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    const w = renderer.domElement.width, h = renderer.domElement.height;
    if (shift.value) camera.setViewOffset(w, h, -w * shift.value, 0, w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    for (const fn of listeners) fn();
    const busy = tweens.size > 0 || moved || (controls.enabled && controls.autoRotate);
    if (busy && !still) requestAnimationFrame(frame);
    else running = false;
  }
  function wake() {
    if (running) return;
    running = true;
    requestAnimationFrame(frame);
  }

  let fitters = [];
  function fit() {
    const w = Math.max(1, container.clientWidth), h = Math.max(1, container.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    for (const fn of fitters) fn(w, h);
    wake();
  }
  new ResizeObserver(fit).observe(container);
  fit();

  const room = {
    box, turn, uniforms, controls, camera, renderer, reduceMotion, shift,

    // --- the scan's frame, in and out ---
    toScan: (x, y) => unturnXY(x, y, turn),
    onFloor: (x, y) => inRoom.has(x, y),

    // A camera view, in the DRAWN frame (the page builds them from box).
    view(position, target, fov = 50) {
      const m = new THREE.Matrix4().lookAt(new THREE.Vector3(...position), new THREE.Vector3(...target), new THREE.Vector3(0, 0, 1));
      return { position: new THREE.Vector3(...position), quaternion: new THREE.Quaternion().setFromRotationMatrix(m), fov, target: new THREE.Vector3(...target) };
    },
    // Where a pin with a camera was taken from, a little wider so the room shows round the photo.
    photoView(pin, widen = 1.3) {
      const m = cameraMatrix(pin);
      const q = new THREE.Quaternion().setFromRotationMatrix(m);
      const position = toDrawn(pin.x, pin.y, pin.z);
      return { position, quaternion: q, fov: pin.camera.vfov * widen, target: position.clone().add(new THREE.Vector3(0, 0, -1).applyQuaternion(q)) };
    },
    // A pin with no camera: look down at its spot from across the room. `far`
    // stands further back on a narrow screen (views.js distanceFor).
    spotView(pin, far = 1) {
      const s = toDrawn(pin.x, pin.y, pin.z);
      const [cx, cy] = box.centre;
      const from = [cx + (cx - s.x) * 0.5, cy + (cy - s.y) * 0.5 - 0.01, 3.7];
      const target = [s.x, s.y, 0.5];
      return room.view(from.map((v, k) => target[k] + (v - target[k]) * far), target, 56);
    },

    // Fly the camera. Resolves true if it got there, false if a newer flight
    // replaced it; only a flight that got there may hand the camera to a drag.
    flyTo(v, ms = 1600, { orbit = false, arc = 0 } = {}) {
      const mine = ++flight;
      controls.enabled = false;
      controls.autoRotate = false;
      const p0 = camera.position.clone(), q0 = camera.quaternion.clone(), f0 = camera.fov;
      return tween("camera", ms, (t) => {
        const e = ease(t);
        camera.position.lerpVectors(p0, v.position, e);
        camera.position.z += arc * Math.sin(Math.PI * e);
        camera.quaternion.slerpQuaternions(q0, v.quaternion, e);
        camera.fov = f0 + (v.fov - f0) * e;
      }).then((arrived) => {
        if (!arrived || mine !== flight) return false;
        if (orbit) { controls.target.copy(v.target); controls.enabled = true; controls.update(); }
        return true;
      });
    },
    jump(v) { return room.flyTo(v, 0); },
    spin(speed) {
      if (reduceMotion || !controls.enabled) return;
      controls.autoRotate = true;
      controls.autoRotateSpeed = speed;
      wake();
    },
    animate(key, uniform, to, ms) {
      const from = uniform.value;
      return tween(key, ms, (t) => (uniform.value = from + (to - from) * ease(t)));
    },

    showPhoto(pin, src, aspect, on = true, ms = 600) {
      if (!pin || !pin.camera) return Promise.resolve(false);
      const material = plane(pin, src, aspect).material, from = material.opacity, to = on ? 1 : 0;
      return tween(`photo${pin.memory}`, ms, (t) => (material.opacity = from + (to - from) * ease(t)));
    },
    hidePhotos(ms = 300) {
      return Promise.all([...planes.values()].map((mesh) => {
        const from = mesh.material.opacity;
        return tween(`photo-hide${mesh.id}`, ms, (t) => (mesh.material.opacity = from * (1 - ease(t))));
      }));
    },

    // A point in the scan's frame, on the page. visible is false behind the camera.
    project(x, y, z) {
      const p = toDrawn(x, y, z).project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height, visible: p.z > -1 && p.z < 1 };
    },
    // The floor under a page position, in the scan's frame, or null.
    floorAt(clientX, clientY) {
      const r = renderer.domElement.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1), camera);
      const hit = ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0), new THREE.Vector3());
      return hit ? unturnXY(hit.x, hit.y, turn) : null;
    },

    onFrame(fn) { listeners.push(fn); },
    onResize(fn) { fitters.push(fn); fn(container.clientWidth, container.clientHeight); },
    redraw: wake,
  };
  return room;
}
