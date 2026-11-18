"""Helpers shared by the rooms tests."""

import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

PASSWORD = "pass-12345-word"


def make_user(username="ana", password=PASSWORD):
    """Create and return an ordinary user."""
    return get_user_model().objects.create_user(username, password=password)


class TempMediaTestCase(TestCase):
    """A TestCase whose uploaded files go to a temporary folder.

    Without this, every test that saves a photo or a video would leave it in
    the project's real media/ folder. The temporary folder is removed when
    the class's tests have finished.
    """

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="memory-room-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)


def jpeg_file(name="photo.jpg", taken=None):
    """A real, tiny JPEG as an uploaded file.

    `taken` is a datetime. When given, it is written inside the photo as its
    capture date, the way a phone camera does.
    """
    image = Image.new("RGB", (8, 8), (200, 120, 60))
    buffer = io.BytesIO()
    if taken is None:
        image.save(buffer, "JPEG")
    else:
        exif = Image.Exif()
        # 0x8769 is the Exif block; 36867 is DateTimeOriginal, the capture date.
        exif.get_ifd(0x8769)[36867] = taken.strftime("%Y:%m:%d %H:%M:%S")
        image.save(buffer, "JPEG", exif=exif)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def video_file(name="room.mp4", size=64):
    """Bytes that begin the way an MP4 or MOV file does, padded to `size`.

    It is not a playable video. It is enough for the app's checks, which look
    at the file's ending, its size and its first bytes.
    """
    start = b"\x00\x00\x00\x18ftypmp42"
    return SimpleUploadedFile(name, start.ljust(size, b"\x00"), content_type="video/mp4")
