// Reading the room's points file in the browser, in the two candidate formats.
//
// Which format the app uses is the builder's open decision. Both are read
// here so the viewer works with either. They are the same two layouts that
// roomgeom/pointsfile.py writes (prebuilt/ai/geometry):
//
//   "bin"  no header; every point's x, y, z as 32-bit floats, then every
//          point's red, green, blue as single bytes. 15 bytes a point.
//   "ply"  a standard binary PLY: a short text header, then per point
//          x, y, z (32-bit floats) and red, green, blue (bytes).
//
// Both functions return { count, positions, colors }:
//   positions  Float32Array, 3 numbers a point (metres; floor z = 0, z up)
//   colors     Uint8Array, 3 numbers a point (0 to 255)

const BYTES_PER_POINT = 15;

export function parseBin(buffer) {
  if (buffer.byteLength % BYTES_PER_POINT !== 0) {
    throw new Error("Not a points file: its size is not a whole number of 15-byte points.");
  }
  const count = buffer.byteLength / BYTES_PER_POINT;
  return {
    count,
    // No copying: these two arrays look straight into the downloaded bytes.
    positions: new Float32Array(buffer, 0, count * 3),
    colors: new Uint8Array(buffer, count * 12, count * 3),
  };
}

const PLY_PROPERTIES = [
  "property float x",
  "property float y",
  "property float z",
  "property uchar red",
  "property uchar green",
  "property uchar blue",
].join("\n");

export function parsePly(buffer) {
  const bytes = new Uint8Array(buffer);
  const start = new TextDecoder("ascii").decode(bytes.subarray(0, Math.min(bytes.length, 4000)));
  const marker = "end_header\n";
  const end = start.indexOf(marker);
  if (!start.startsWith("ply\n") || end < 0) {
    throw new Error("Not a PLY file.");
  }
  const header = start.slice(0, end);
  const vertex = header.match(/^element vertex (\d+)$/m);
  const properties = header.split("\n").filter((line) => line.startsWith("property ")).join("\n");
  // Only the one layout Memory Room writes is accepted. Anything else is
  // refused, so a file with another layout fails loudly and is never misread.
  if (!header.includes("format binary_little_endian 1.0") || !vertex || properties !== PLY_PROPERTIES) {
    throw new Error("This PLY does not have the layout Memory Room writes.");
  }
  const count = Number(vertex[1]);
  const bodyStart = end + marker.length;
  if (bytes.length - bodyStart !== count * BYTES_PER_POINT) {
    throw new Error("This PLY is cut short or has extra data.");
  }
  // In a PLY each point's numbers sit together, so they are copied out one
  // point at a time into the two arrays the viewer wants.
  const view = new DataView(buffer, bodyStart);
  const positions = new Float32Array(count * 3);
  const colors = new Uint8Array(count * 3);
  for (let i = 0; i < count; i++) {
    const at = i * BYTES_PER_POINT;
    positions[i * 3] = view.getFloat32(at, true);
    positions[i * 3 + 1] = view.getFloat32(at + 4, true);
    positions[i * 3 + 2] = view.getFloat32(at + 8, true);
    colors[i * 3] = view.getUint8(at + 12);
    colors[i * 3 + 1] = view.getUint8(at + 13);
    colors[i * 3 + 2] = view.getUint8(at + 14);
  }
  return { count, positions, colors };
}

// Download a points file and read it. `format` is "bin" or "ply"; when left
// out it is taken from the end of the address.
export async function loadPoints(url, format) {
  const kind = format || (String(url).split("?")[0].toLowerCase().endsWith(".ply") ? "ply" : "bin");
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`The room's points could not be loaded (${response.status}).`);
  }
  const buffer = await response.arrayBuffer();
  return kind === "ply" ? parsePly(buffer) : parseBin(buffer);
}
