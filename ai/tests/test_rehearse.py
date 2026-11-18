"""Tests for rehearse_notebook.py's work folder check: it must never empty a folder it did not make."""

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `import rehearse_notebook` works when run from elsewhere

try:
    import rehearse_notebook  # noqa: E402  (needs opencv and IPython)
except ImportError as missing:  # pragma: no cover
    rehearse_notebook = None
    MISSING = str(missing)


@unittest.skipIf(rehearse_notebook is None, "needs opencv and IPython (ai/requirements.txt)")
class WorkFolderTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="rehearse-test-"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.parent, ignore_errors=True)

    def test_a_folder_holding_other_files_is_refused_and_left_alone(self):
        # Review, 18 Nov: `rehearse_notebook.py .` from the project root deleted the project.
        work = self.parent / "busy"
        work.mkdir()
        (work / "keep.txt").write_text("my work")
        with self.assertRaises(SystemExit):
            rehearse_notebook.check_work_folder(work)
        self.assertEqual((work / "keep.txt").read_text(), "my work")

    def test_a_new_or_empty_folder_is_accepted(self):
        rehearse_notebook.check_work_folder(self.parent / "new")
        empty = self.parent / "empty"
        empty.mkdir()
        rehearse_notebook.check_work_folder(empty)

    def test_a_folder_from_an_earlier_rehearsal_is_accepted(self):
        work = self.parent / "earlier"
        work.mkdir()
        (work / rehearse_notebook.MARKER).write_text("")
        (work / "room.mp4").write_bytes(b"old")
        rehearse_notebook.check_work_folder(work)


if __name__ == "__main__":
    unittest.main()
