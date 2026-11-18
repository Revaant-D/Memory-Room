// Plain geometry for the room page: no three.js, so Node can test it
// (static/viewer/tests/roomgeom.test.mjs).
//
// Positions are a Float32Array of x, y, z per point: metres, floor at z = 0, z up,
// in the scan's own frame.

// Turn a point about the z axis by `a` radians (anticlockwise seen from above).
export function turnXY(x, y, a) {
  const c = Math.cos(a), s = Math.sin(a);
  return [c * x - s * y, s * x + c * y];
}

// The exact inverse of turnXY: a tap on the turned room, back in the scan's frame.
export function unturnXY(x, y, a) {
  return turnXY(x, y, -a);
}

// The turn that lines a room's walls up with the x and y axes, in [0, pi/2).
//
// A scan is not wall-aligned. Turned the right way, the points on its walls pile
// up into a few narrow columns along x and along y, so a histogram of their x
// (and of their y) is as peaked as it gets. The search keeps the turn with the
// most peaked histograms. `step` keeps every n-th
// point, for speed on a 400,000-point room.
export function wallAngle(positions, step = 7) {
  const xs = [], ys = [];
  for (let i = 0; i < positions.length; i += 3 * step) {
    const z = positions[i + 2];
    if (z > 0.3 && z < 2.3) { xs.push(positions[i]); ys.push(positions[i + 1]); }
  }
  if (xs.length < 10) return 0;
  const BIN = 0.02;
  function score(d) {
    const a = (d * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
    const hx = new Map(), hy = new Map();
    for (let k = 0; k < xs.length; k++) {
      const bx = Math.floor((c * xs[k] - s * ys[k]) / BIN);
      const by = Math.floor((s * xs[k] + c * ys[k]) / BIN);
      hx.set(bx, (hx.get(bx) || 0) + 1);
      hy.set(by, (hy.get(by) || 0) + 1);
    }
    // Each bin is counted with its neighbour, so a wall that falls on a bin
    // edge (split in two by rounding) still counts as one peak.
    let total = 0;
    for (const h of [hx, hy]) {
      for (const [b, n] of h) { const pair = n + (h.get(b + 1) || 0); total += pair * pair; }
    }
    return total;
  }
  // Every 2 degrees first, then every quarter degree around the best: about
  // 60 tries instead of 360, so a phone does it in a fraction of a second.
  let best = 0, bestScore = -1;
  for (let d = 0; d < 90; d += 2) {
    const sc = score(d);
    if (sc > bestScore) { bestScore = sc; best = d; }
  }
  const around = best;
  for (let d = around - 2; d <= around + 2; d += 0.25) {
    const sc = score(d);
    if (sc > bestScore) { bestScore = sc; best = d; }
  }
  const turn = (((best % 90) + 90) % 90) * Math.PI / 180;
  return turn;
}

// Where the room is, seen from above: every 10 cm cell that has a point under
// 2 m (floor, furniture, walls; not the ceiling, which can span past the walls).
// has(x, y) also accepts the eight cells around, so a sparse patch of floor
// still counts. Used to refuse a tap outside the room, such as the empty
// corner of an L-shaped room that its box still covers.
export function footprint(positions, cell = 0.1) {
  const cells = new Set();
  const key = (i, j) => `${i},${j}`;
  for (let i = 0; i < positions.length; i += 3) {
    if (positions[i + 2] < 2.0) {
      cells.add(key(Math.floor(positions[i] / cell), Math.floor(positions[i + 1] / cell)));
    }
  }
  return {
    has(x, y) {
      const ci = Math.floor(x / cell), cj = Math.floor(y / cell);
      for (let di = -1; di <= 1; di++) {
        for (let dj = -1; dj <= 1; dj++) if (cells.has(key(ci + di, cj + dj))) return true;
      }
      return false;
    },
  };
}
