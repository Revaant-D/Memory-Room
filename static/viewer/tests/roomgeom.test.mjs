// Tests for static/viewer/roomgeom.js. Run: node --test static/viewer/tests/
import { test } from "node:test";
import assert from "node:assert/strict";

import { footprint, turnXY, unturnXY, wallAngle } from "../roomgeom.js";

const deg = (d) => (d * Math.PI) / 180;

// Points on the four walls of a 4 x 3 m room, 0 to 2.5 m up, then turned by `by`.
function boxWalls(by) {
  const out = [];
  for (let z = 0; z <= 2.5; z += 0.1) {
    for (let t = 0; t <= 4; t += 0.02) { out.push([t, 0, z], [t, 3, z]); }
    for (let t = 0; t <= 3; t += 0.02) { out.push([0, t, z], [4, t, z]); }
  }
  const flat = new Float32Array(out.length * 3);
  out.forEach(([x, y, z], i) => {
    const [tx, ty] = turnXY(x, y, by);
    flat.set([tx, ty, z], i * 3);
  });
  return flat;
}

test("wallAngle finds the turn that lines the walls up with the axes", () => {
  // The walls were turned by -20 degrees, so turning by +20 lines them up.
  const angle = wallAngle(boxWalls(deg(-20)), 1);
  assert.ok(Math.abs(angle - deg(20)) <= deg(0.5), `got ${(angle * 180) / Math.PI} degrees`);
});

test("wallAngle answers 0 for a room that is already lined up", () => {
  const angle = wallAngle(boxWalls(0), 1);
  assert.ok(angle <= deg(0.5) || angle >= deg(89.5), `got ${(angle * 180) / Math.PI} degrees`);
});

test("unturnXY undoes turnXY exactly", () => {
  for (const a of [0, 0.3, 1.2, -0.7]) {
    for (const [x, y] of [[1.25, -0.5], [0, 0], [-3.1, 2.7]]) {
      const [tx, ty] = turnXY(x, y, a);
      const [bx, by] = unturnXY(tx, ty, a);
      assert.ok(Math.abs(bx - x) < 1e-9 && Math.abs(by - y) < 1e-9, `angle ${a}: (${x}, ${y}) came back as (${bx}, ${by})`);
    }
  }
});

// An L-shaped room: a 4 x 2 m part along x, and a 2 x 2 m part above its left end.
// The empty corner of the L (x 2..4, y 2..4) has no points. A bed (x 0.2..1.8,
// y 2.2..3.8) hides the floor under it: only its top, 0.6 m up, was filmed.
function lRoom() {
  const out = [];
  const inBed = (x, y) => x > 0.2 && x < 1.8 && y > 2.2 && y < 3.8;
  for (let x = 0; x <= 4; x += 0.05) {
    for (let y = 0; y <= 4; y += 0.05) {
      const inRoom = y <= 2 || x <= 2;
      if (!inRoom) continue;
      out.push(inBed(x, y) ? [x, y, 0.6] : [x, y, 0]);
    }
  }
  return new Float32Array(out.flat());
}

test("footprint says yes on the floor and on the bed, no in the L's empty corner", () => {
  const room = footprint(lRoom());
  assert.equal(room.has(1, 1), true, "open floor");
  assert.equal(room.has(1, 3), true, "on the bed, where the floor was never filmed");
  assert.equal(room.has(3.2, 3.2), false, "the empty corner of the L");
  assert.equal(room.has(9, 9), false, "far outside");
});

test("footprint ignores the ceiling", () => {
  // Ceiling points over the whole box would otherwise fill the empty corner.
  const ceiling = [];
  for (let x = 0; x <= 4; x += 0.05) for (let y = 0; y <= 4; y += 0.05) ceiling.push(x, y, 2.6);
  const both = new Float32Array([...lRoom(), ...ceiling]);
  assert.equal(footprint(both).has(3.2, 3.2), false);
});
