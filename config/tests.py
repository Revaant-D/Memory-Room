"""Tests for config/secret.py: where the app's secret key comes from."""

import os
import tempfile
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.secret import KEY_FILE_NAME, load_secret_key


class LoadSecretKeyTests(SimpleTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base_dir = Path(folder.name)
        self.key_file = self.base_dir / KEY_FILE_NAME

        # Every test starts with no key in the environment, whatever the
        # machine running the tests has set.
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("DJANGO_SECRET_KEY", None)

    def test_key_file_name(self):
        # .gitignore lists this exact name. If it changes here, it must change there.
        self.assertEqual(KEY_FILE_NAME, ".secret_key")

    def test_env_var_wins(self):
        os.environ["DJANGO_SECRET_KEY"] = "from-env"
        self.assertEqual(load_secret_key(self.base_dir), "from-env")
        self.assertFalse(self.key_file.exists())

    def test_env_var_wins_over_key_file(self):
        self.key_file.write_text("from-file", encoding="utf-8")
        os.environ["DJANGO_SECRET_KEY"] = "from-env"
        self.assertEqual(load_secret_key(self.base_dir), "from-env")

    def test_blank_env_var_is_ignored(self):
        os.environ["DJANGO_SECRET_KEY"] = "   "
        key = load_secret_key(self.base_dir)
        self.assertGreaterEqual(len(key), 50)
        self.assertTrue(self.key_file.exists())

    def test_creates_key_file(self):
        key = load_secret_key(self.base_dir)
        self.assertGreaterEqual(len(key), 50)
        self.assertEqual(self.key_file.read_text(encoding="utf-8"), key)

    def test_reuses_key_file(self):
        first = load_secret_key(self.base_dir)
        second = load_secret_key(self.base_dir)
        self.assertEqual(first, second)

    def test_new_keys_differ(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertNotEqual(
                load_secret_key(self.base_dir), load_secret_key(Path(other))
            )

    def test_key_file_whitespace_is_stripped(self):
        self.key_file.write_text("  from-file\n", encoding="utf-8")
        self.assertEqual(load_secret_key(self.base_dir), "from-file")

    def test_blank_key_file_is_replaced(self):
        self.key_file.write_text("\n", encoding="utf-8")
        key = load_secret_key(self.base_dir)
        self.assertGreaterEqual(len(key), 50)
        self.assertEqual(self.key_file.read_text(encoding="utf-8"), key)

    def test_key_file_with_byte_order_mark(self):
        # Notepad and PowerShell 5 put an invisible mark at the start of a
        # UTF-8 file. It must not become part of the key.
        self.key_file.write_bytes(b"\xef\xbb\xbffrom-file")
        self.assertEqual(load_secret_key(self.base_dir), "from-file")

    def test_key_file_in_wrong_encoding_gives_clear_error(self):
        # PowerShell 5's `echo key > .secret_key` writes UTF-16, not UTF-8.
        self.key_file.write_bytes("from-file".encode("utf-16"))
        with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_SECRET_KEY"):
            load_secret_key(self.base_dir)

    def test_unwritable_folder_gives_clear_error(self):
        missing = self.base_dir / "no-such-folder"
        with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_SECRET_KEY"):
            load_secret_key(missing)
