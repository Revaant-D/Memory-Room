"""Tests for photos (memories).

This file holds the tests that are the same whatever is decided for D2 (how
photos are added) and D3 (who can fetch a photo file): reading a photo's
date, checking a photo file, and the caption-and-date form. The rest of
chunk 5's tests are added here when chunk 5 is built.
"""

import datetime
import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from PIL import Image

from rooms.forms import MemoryForm
from rooms.photos import photo_taken_on
from rooms.tests.utils import jpeg_file
from rooms.validators import validate_photo


def image_file(kind, name):
    """A real, tiny image in the given Pillow format ("PNG", "WEBP", "GIF")."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (60, 120, 200)).save(buffer, kind)
    return SimpleUploadedFile(name, buffer.getvalue())


def jpeg_with_date_text(text):
    """A JPEG whose capture-date field holds `text`, whatever it is."""
    exif = Image.Exif()
    exif.get_ifd(0x8769)[36867] = text
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, "JPEG", exif=exif)
    return SimpleUploadedFile("photo.jpg", buffer.getvalue())


class PhotoDateTests(SimpleTestCase):
    def test_date_read_from_photo(self):
        photo = jpeg_file(taken=datetime.datetime(2026, 5, 9, 14, 3))
        self.assertEqual(photo_taken_on(photo), datetime.date(2026, 5, 9))

    def test_no_date_in_photo(self):
        self.assertIsNone(photo_taken_on(jpeg_file()))

    def test_garbled_date(self):
        self.assertIsNone(photo_taken_on(jpeg_with_date_text("not a date")))

    def test_impossible_date(self):
        # Some cameras with no clock set write zeros.
        self.assertIsNone(photo_taken_on(jpeg_with_date_text("0000:00:00 00:00:00")))

    def test_file_change_date_is_the_fallback(self):
        exif = Image.Exif()
        exif[306] = "2026:03:01 09:00:00"
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8)).save(buffer, "JPEG", exif=exif)
        photo = SimpleUploadedFile("photo.jpg", buffer.getvalue())
        self.assertEqual(photo_taken_on(photo), datetime.date(2026, 3, 1))

    def test_not_an_image(self):
        self.assertIsNone(photo_taken_on(SimpleUploadedFile("notes.jpg", b"just some text")))

    def test_file_left_rewound(self):
        for photo in (jpeg_file(taken=datetime.datetime(2026, 5, 9)), jpeg_file()):
            photo.read(5)
            photo_taken_on(photo)
            self.assertEqual(photo.tell(), 0)


class PhotoCheckTests(SimpleTestCase):
    def test_jpeg_png_webp_accepted(self):
        validate_photo(jpeg_file())
        validate_photo(image_file("PNG", "photo.png"))
        validate_photo(image_file("WEBP", "photo.webp"))

    def test_the_name_is_not_what_is_checked(self):
        # A real JPEG is accepted whatever it is called; the content decides.
        validate_photo(jpeg_file("photo.dat"))

    def test_gif_refused(self):
        message = "Upload JPEG, PNG or WebP photos. HEIC is not supported yet."
        with self.assertRaisesMessage(ValidationError, message):
            validate_photo(image_file("GIF", "photo.gif"))

    def test_text_file_named_jpg(self):
        with self.assertRaises(ValidationError):
            validate_photo(SimpleUploadedFile("notes.jpg", b"just some text"))

    def test_heic_refused(self):
        # The first bytes of an iPhone HEIC photo. Pillow cannot open it.
        heic = SimpleUploadedFile("IMG_0001.heic", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64)
        with self.assertRaisesMessage(ValidationError, "HEIC is not supported yet"):
            validate_photo(heic)

    @override_settings(MAX_PHOTO_BYTES=10)
    def test_too_large(self):
        with self.assertRaisesMessage(ValidationError, "too large"):
            validate_photo(jpeg_file())

    def test_size_limit_message(self):
        # The real limit, without making a 20 MB file: claim the size instead.
        big = SimpleUploadedFile("photo.jpg", b"x")
        big.size = 20 * 1024 * 1024 + 1
        with self.assertRaisesMessage(ValidationError, "The limit is 20 MB."):
            validate_photo(big)

    def test_check_leaves_file_rewound(self):
        photo = jpeg_file()
        validate_photo(photo)
        self.assertEqual(photo.tell(), 0)


class MemoryFormTests(SimpleTestCase):
    """The form for a photo's caption and date. The photo itself is not on it."""

    def test_empty_caption_and_date_are_fine(self):
        form = MemoryForm({"caption": "", "taken_on": ""})
        self.assertTrue(form.is_valid())

    def test_caption_too_long(self):
        self.assertTrue(MemoryForm({"caption": "x" * 200}).is_valid())
        self.assertFalse(MemoryForm({"caption": "x" * 201}).is_valid())

    def test_future_date_refused(self):
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        form = MemoryForm({"caption": "", "taken_on": tomorrow.isoformat()})
        self.assertEqual(form.errors["taken_on"], ["The date can't be in the future."])

    def test_date_can_be_cleared(self):
        form = MemoryForm({"caption": "Move-in day", "taken_on": ""})
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["taken_on"])

    def test_today_is_allowed(self):
        form = MemoryForm({"caption": "", "taken_on": timezone.localdate().isoformat()})
        self.assertTrue(form.is_valid())
