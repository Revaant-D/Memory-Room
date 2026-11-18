// Mockup engine: the builder's real room (393,033 points) and the real camera
// poses of seven video frames, which stand in for photos.
// Shared by the three design mockups. Not app code.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

THREE.ColorManagement.enabled = false;

export const PLY_URL = "/media/places/1/scans/c9fe1b381f8a4fe4bbdc2938369c04eb-points.ply";
export const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

async function readPly(url) {
  const buffer = await (await fetch(url)).arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const head = new TextDecoder("ascii").decode(bytes.subarray(0, 2000));
  const end = head.indexOf("end_header\n") + 11;
  const count = Number(head.match(/element vertex (\d+)/)[1]);
  const view = new DataView(buffer, end);
  const positions = new Float32Array(count * 3);
  const colors = new Uint8Array(count * 3);
  for (let i = 0; i < count; i++) {
    const at = i * 15;
    positions[i * 3] = view.getFloat32(at, true);
    positions[i * 3 + 1] = view.getFloat32(at + 4, true);
    positions[i * 3 + 2] = view.getFloat32(at + 8, true);
    colors[i * 3] = bytes[end + at + 12];
    colors[i * 3 + 1] = bytes[end + at + 13];
    colors[i * 3 + 2] = bytes[end + at + 14];
  }
  return { count, positions, colors };
}

const VERT = /* glsl */ `
  attribute vec3 color;
  attribute vec3 scatter;
  uniform float size, scale, spread, time, nearCut;
  varying vec3 vColor;
  varying float vZ;
  varying float vNear;
  void main() {
    vColor = color;
    vZ = position.z;
    vec3 p = position + scatter * spread + vec3(0.0, 0.0, sin(time + scatter.x * 9.0) * 0.04 * spread);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vNear = -mv.z - nearCut;
    gl_PointSize = clamp(size * scale / -mv.z, 1.0, mix(64.0, 5.0, min(spread * 4.0, 1.0)));
    gl_Position = projectionMatrix * mv;
  }`;

const FRAG = /* glsl */ `
  uniform vec3 tint, floorColor;
  uniform float tintAmount, cut, floorFade, opacity, round;
  varying vec3 vColor;
  varying float vZ;
  varying float vNear;
  void main() {
    if (vZ > cut || vNear < 0.0) discard;
    if (round > 0.5 && length(gl_PointCoord - 0.5) > 0.5) discard;
    vec3 c = mix(vColor, tint, tintAmount);
    c = mix(c, floorColor, floorFade * (1.0 - smoothstep(0.04, 0.12, vZ)));
    gl_FragColor = vec4(c, opacity);
  }`;

// The room arrives rotated so its walls line up with the screen (the scan is not wall-aligned).
export async function createRoom(container, options = {}) {
  const data = await (await fetch(options.dataUrl || "room-data.json")).json();
  const ply = await readPly(PLY_URL);
  const turn = THREE.MathUtils.degToRad(data.angle_deg);
  const R = new THREE.Matrix4().makeRotationZ(turn);

  // Rotate the points once, here, so every later number is in the turned frame.
  const pos = ply.positions;
  const cs = Math.cos(turn), sn = Math.sin(turn);
  const low = [Infinity, Infinity, Infinity], high = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < ply.count; i++) {
    const x = pos[i * 3], y = pos[i * 3 + 1];
    pos[i * 3] = cs * x - sn * y;
    pos[i * 3 + 1] = sn * x + cs * y;
    for (let k = 0; k < 3; k++) {
      low[k] = Math.min(low[k], pos[i * 3 + k]);
      high[k] = Math.max(high[k], pos[i * 3 + k]);
    }
  }
  const box = { low, high, centre: low.map((v, k) => (v + high[k]) / 2), size: low.map((v, k) => high[k] - v) };

  // Each photo: where the camera stood and how it looked, turned like the room.
  const flip = new THREE.Matrix4().makeScale(1, -1, -1);
  for (const photo of data.photos) {
    const m = new THREE.Matrix4().set(...photo.pose.flat());
    photo.matrix = R.clone().multiply(m).multiply(flip);
    photo.position = new THREE.Vector3().setFromMatrixPosition(photo.matrix);
    photo.quaternion = new THREE.Quaternion().setFromRotationMatrix(photo.matrix);
    photo.vfov = THREE.MathUtils.radToDeg(2 * Math.atan(data.height / 2 / photo.K[1][1]));
  }
  data.path = data.path.map(([x, y, z]) => [cs * x - sn * y, sn * x + cs * y, z]);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.style.cssText = "display:block;width:100%;height:100%;touch-action:none";
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.03, 300);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enabled = false;

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(ply.colors, 3, true));
  const scatter = new Float32Array(ply.count * 3);
  for (let i = 0; i < scatter.length; i++) scatter[i] = (Math.random() - 0.5) * 4;
  geometry.setAttribute("scatter", new THREE.BufferAttribute(scatter, 3));

  const u = {
    size: { value: options.pointSize ?? 0.028 },
    scale: { value: 1 },
    spread: { value: 0 },
    time: { value: 0 },
    nearCut: { value: 0 },
    tint: { value: new THREE.Color(options.tint ?? 0x333333) },
    tintAmount: { value: 0 },
    floorColor: { value: new THREE.Color(options.floorColor ?? 0xffffff) },
    floorFade: { value: 0 },
    cut: { value: 99 },
    opacity: { value: 1 },
    round: { value: options.round ? 1 : 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms: u, vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: true,
  });
  scene.add(new THREE.Points(geometry, material));

  // A photo shown exactly where it lines up with the room, filling its own view.
  const loader = new THREE.TextureLoader();
  const frames = new Map();
  function photoPlane(photo) {
    if (frames.has(photo.id)) return frames.get(photo.id);
    const d = 0.5;
    const h = 2 * d * Math.tan(THREE.MathUtils.degToRad(photo.vfov) / 2);
    const tex = loader.load(photo.src, () => (needsDraw = true));
    tex.colorSpace = THREE.NoColorSpace;
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(h * (data.width / data.height), h),
      new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, depthTest: false }),
    );
    mesh.renderOrder = 10;
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(photo.matrix).multiply(new THREE.Matrix4().makeTranslation(0, 0, -d));
    scene.add(mesh);
    frames.set(photo.id, mesh);
    return mesh;
  }

  // Tweens: one per key, so a new move replaces an unfinished one.
  const tweens = new Map();
  function tween(key, duration, step) {
    return new Promise((resolve) => {
      if (tweens.has(key)) tweens.get(key).resolve();
      if (reduceMotion || duration <= 0) { step(1); resolve(); return; }
      tweens.set(key, { start: performance.now(), duration, step, resolve });
    });
  }
  function animate(key, target, value, duration) {
    const from = target.value;
    return tween(key, duration, (t) => (target.value = from + (value - from) * ease(t)));
  }

  let needsDraw = true;
  const listeners = [];
  // Slides the picture sideways (a share of the width) without moving the camera.
  const shift = { value: 0 };
  function fit() {
    const w = Math.max(1, container.clientWidth), h = Math.max(1, container.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    needsDraw = true;
  }
  new ResizeObserver(fit).observe(container);
  fit();

  renderer.setAnimationLoop((now) => {
    for (const [key, tw] of tweens) {
      const t = Math.min(1, Math.max(0, (now - tw.start) / tw.duration));
      tw.step(t);
      if (t >= 1) { tweens.delete(key); tw.resolve(); }
    }
    if (controls.enabled) controls.update();
    u.time.value = now / 1000;
    u.scale.value = renderer.domElement.height / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    const w = renderer.domElement.width, h = renderer.domElement.height;
    if (shift.value) camera.setViewOffset(w, h, -w * shift.value, 0, w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    for (const fn of listeners) fn();
  });

  const room = {
    THREE, data, box, camera, controls, uniforms: u, renderer, material, count: ply.count,
    photos: data.photos,
    shift,
    onFrame(fn) { listeners.push(fn); },
    animate,
    // A view looking at `target` from `position`.
    view(position, target, fov = 50) {
      const m = new THREE.Matrix4().lookAt(new THREE.Vector3(...position), new THREE.Vector3(...target), new THREE.Vector3(0, 0, 1));
      return { position: new THREE.Vector3(...position), quaternion: new THREE.Quaternion().setFromRotationMatrix(m), fov, target: new THREE.Vector3(...target) };
    },
    // The view the photo was taken from, a little wider so the room shows around it.
    photoView(photo, widen = 1.25) {
      const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(photo.quaternion);
      return { position: photo.position.clone(), quaternion: photo.quaternion.clone(), fov: photo.vfov * widen, target: photo.position.clone().add(fwd) };
    },
    // A hand-placed photo has a spot but no direction: stand there and face the room's middle.
    viewFor(photo, widen = 1.25) {
      if (photo.quaternion) return this.photoView(photo, widen);
      return this.view(photo.spot.toArray(), [box.centre[0], box.centre[1], photo.spot.z - 0.1], 60);
    },
    jump(v) { this.flyTo(v, 0); },
    flyTo(v, duration = 1600, { orbit = false, arc = 0 } = {}) {
      controls.enabled = false;
      const p0 = camera.position.clone(), q0 = camera.quaternion.clone(), f0 = camera.fov;
      const lift = new THREE.Vector3(0, 0, arc);
      return tween("camera", duration, (t) => {
        const e = ease(t);
        camera.position.lerpVectors(p0, v.position, e).addScaledVector(lift, Math.sin(Math.PI * e));
        camera.quaternion.slerpQuaternions(q0, v.quaternion, e);
        camera.fov = f0 + (v.fov - f0) * e;
      }).then(() => {
        if (orbit) { controls.target.copy(v.target); controls.enabled = true; controls.update(); }
      });
    },
    showPhoto(photo, show = true, duration = 600) {
      if (!photo.matrix) return Promise.resolve();
      const mat = photoPlane(photo).material;
      const from = mat.opacity, to = show ? 1 : 0;
      return tween("photo" + photo.id, duration, (t) => (mat.opacity = from + (to - from) * ease(t)));
    },
    hideAllPhotos(duration = 400) {
      return Promise.all([...frames.keys()].map((id) => data.photos.find((p) => p.id === id)).filter((p) => frames.has(p.id)).map((p) => room.showPhoto(p, false, duration)));
    },
    // Where a 3D point is on the page.
    project(v) {
      const p = (v.isVector3 ? v.clone() : new THREE.Vector3(...v)).project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height, visible: p.z > -1 && p.z < 1 };
    },
    // Tap the floor: the floor point under a page position, or null.
    floorAt(clientX, clientY) {
      const r = renderer.domElement.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1), camera);
      return ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0), new THREE.Vector3());
    },
  };
  return room;
}
