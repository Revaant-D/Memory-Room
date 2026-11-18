"""Tests for roomgeom.pointsfile: both candidate formats, written and read back.

    python -m unittest discover -s tests
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from roomgeom.pointsfile import BYTES_PER_POINT, READERS, WRITERS, read_bin, read_ply, write_bin, write_ply


class PointsFileTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(4)
        self.points = rng.uniform(-3, 3, size=(500, 3))
        self.colors = rng.integers(0, 256, size=(500, 3))
        self.folder = tempfile.TemporaryDirectory()
        self.dir = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_both_formats_give_back_what_was_written(self):
        for kind in ("bin", "ply"):
            path = self.dir / f"room.{kind}"
            self.assertEqual(WRITERS[kind](path, self.points, self.colors), 500)
            points, colors = READERS[kind](path)
            # Positions are stored as 32-bit floats: good to a few thousandths of a millimetre here.
            np.testing.assert_allclose(points, self.points, atol=1e-6)
            np.testing.assert_array_equal(colors, self.colors)
            self.assertEqual(points.dtype, np.float32)
            self.assertEqual(colors.dtype, np.uint8)

    def test_sizes(self):
        write_bin(self.dir / "room.bin", self.points, self.colors)
        write_ply(self.dir / "room.ply", self.points, self.colors)
        bin_size = (self.dir / "room.bin").stat().st_size
        ply_size = (self.dir / "room.ply").stat().st_size
        self.assertEqual(bin_size, 500 * BYTES_PER_POINT)
        header = ply_size - bin_size
        self.assertTrue(0 < header < 300)  # the PLY costs only its header

    def test_bin_layout_is_the_one_the_design_sketch_reads(self):
        # The viewer sketch: Float32Array(buf, 0, n*3) then Uint8Array(buf, n*12, n*3).
        write_bin(self.dir / "room.bin", self.points, self.colors)
        raw = (self.dir / "room.bin").read_bytes()
        xyz = np.frombuffer(raw, dtype="<f4", count=500 * 3)
        rgb = np.frombuffer(raw, dtype=np.uint8, offset=500 * 12, count=500 * 3)
        np.testing.assert_allclose(xyz.reshape(500, 3), self.points, atol=1e-6)
        np.testing.assert_array_equal(rgb.reshape(500, 3), self.colors)

    def test_ply_header_is_standard(self):
        write_ply(self.dir / "room.ply", self.points, self.colors)
        head = (self.dir / "room.ply").read_bytes()[:400].decode("ascii", errors="replace")
        self.assertTrue(head.startswith("ply\nformat binary_little_endian 1.0\n"))
        self.assertIn("element vertex 500\n", head)
        self.assertIn("property uchar blue\nend_header\n", head)

    def test_no_colours_means_grey(self):
        write_ply(self.dir / "room.ply", self.points)
        _, colors = read_ply(self.dir / "room.ply")
        self.assertTrue((colors == 128).all())

    def test_empty_room(self):
        for kind in ("bin", "ply"):
            path = self.dir / f"empty.{kind}"
            self.assertEqual(WRITERS[kind](path, np.zeros((0, 3)), np.zeros((0, 3), dtype=np.uint8)), 0)
            points, colors = READERS[kind](path)
            self.assertEqual(points.shape, (0, 3))
            self.assertEqual(colors.shape, (0, 3))

    def test_bad_input_is_refused(self):
        path = self.dir / "room.bin"
        with self.assertRaises(ValueError):
            write_bin(path, self.points[:, :2], self.colors)  # not N x 3
        with self.assertRaises(ValueError):
            write_bin(path, self.points, self.colors[:10])  # colours do not match
        with self.assertRaises(ValueError):
            write_bin(path, self.points, self.colors / 255.0)  # colours as 0.0 to 1.0
        with self.assertRaises(ValueError):
            write_bin(path, self.points, self.colors + 300)  # out of range
        broken = self.points.copy()
        broken[3, 1] = np.nan
        with self.assertRaises(ValueError):
            write_ply(path, broken, self.colors)
        self.assertFalse(path.exists())  # nothing half-written

    def test_damaged_files_are_refused(self):
        write_bin(self.dir / "room.bin", self.points, self.colors)
        write_ply(self.dir / "room.ply", self.points, self.colors)
        raw = (self.dir / "room.bin").read_bytes()
        (self.dir / "short.bin").write_bytes(raw[:-7])
        with self.assertRaises(ValueError):
            read_bin(self.dir / "short.bin")
        ply = (self.dir / "room.ply").read_bytes()
        (self.dir / "short.ply").write_bytes(ply[:-15])
        with self.assertRaises(ValueError):
            read_ply(self.dir / "short.ply")
        (self.dir / "other.ply").write_bytes(ply.replace(b"property uchar red\n", b"property float nx\n"))
        with self.assertRaises(ValueError):
            read_ply(self.dir / "other.ply")
        (self.dir / "text.ply").write_bytes(b"this is not a ply file")
        with self.assertRaises(ValueError):
            read_ply(self.dir / "text.ply")


if __name__ == "__main__":
    unittest.main()
