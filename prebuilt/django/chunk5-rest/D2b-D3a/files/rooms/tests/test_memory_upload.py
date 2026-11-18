"""Tests for adding a photo: one per form, with its caption and date (decision D2, option b)."""

import datetime
import io
import os

from django.conf import settings
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from PIL import Image

from rooms.forms import MemoryUploadForm
from rooms.models import Memory, Place
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user


def upload_form(photo, caption="", taken_on=""):
    """A MemoryUploadForm as if a person had submitted it."""
    files = {"photo": photo} if photo is not None else {}
    return MemoryUploadForm({"caption": caption, "taken_on": taken_on}, files)


def text_file(name="notes.jpg"):
    return SimpleUploadedFile(name, b"just some text")


def gif_file(name="photo.gif"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, "GIF")
    return SimpleUploadedFile(name, buffer.getvalue())


def files_on_disk():
    return sum(len(names) for _, _, names in os.walk(settings.MEDIA_ROOT))


class MemoryUploadFormTests(SimpleTestCase):
    def test_one_photo_valid(self):
        self.assertTrue(upload_form(jpeg_file()).is_valid())

    def test_caption_and_date_are_optional_but_kept(self):
        form = upload_form(jpeg_file(), caption="Move-in day", taken_on="2026-05-09")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["caption"], "Move-in day")
        self.assertEqual(form.cleaned_data["taken_on"], datetime.date(2026, 5, 9))

    def test_text_file_named_jpg(self):
        self.assertFalse(upload_form(text_file("notes.jpg")).is_valid())

    def test_gif_refused(self):
        form = upload_form(gif_file())
        self.assertEqual(
            form.errors["photo"], ["Upload JPEG, PNG or WebP photos. HEIC is not supported yet."]
        )

    def test_heic_refused(self):
        heic = SimpleUploadedFile("IMG_0001.heic", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64)
        form = upload_form(heic)
        self.assertFalse(form.is_valid())
        self.assertIn("HEIC is not supported yet", form.errors["photo"][0])

    def test_empty_file_refused(self):
        self.assertFalse(upload_form(SimpleUploadedFile("empty.jpg", b"")).is_valid())

    @override_settings(MAX_PHOTO_BYTES=10)
    def test_too_large(self):
        self.assertIn("too large", upload_form(jpeg_file()).errors["photo"][0])

    def test_no_file(self):
        self.assertEqual(upload_form(None).errors["photo"], ["This field is required."])

    def test_long_file_name_accepted(self):
        self.assertTrue(upload_form(jpeg_file("x" * 196 + ".jpg")).is_valid())

    def test_caption_too_long(self):
        self.assertFalse(upload_form(jpeg_file(), caption="x" * 201).is_valid())

    def test_future_date_refused(self):
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        form = upload_form(jpeg_file(), taken_on=tomorrow.isoformat())
        self.assertEqual(form.errors["taken_on"], ["The date can't be in the future."])

    def test_input_takes_one_photo(self):
        html = str(MemoryUploadForm()["photo"])
        self.assertNotIn("multiple", html)
        self.assertIn('accept="image/jpeg,image/png,image/webp"', html)

    def test_help_text_states_the_limit(self):
        self.assertIn("up to 20 MB", MemoryUploadForm()["photo"].help_text)


class MemoryUploadPageTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="Dorm")
        self.client.force_login(self.ana)
        self.url = "/places/dorm/memories/new/"

    def upload(self, photo, caption="", taken_on="", **kwargs):
        data = {"photo": photo, "caption": caption, "taken_on": taken_on}
        return self.client.post(self.url, data, **kwargs)

    def test_page_needs_login(self):
        self.client.logout()
        for response in (self.client.get(self.url), self.upload(jpeg_file())):
            self.assertRedirects(
                response, f"/accounts/login/?next={self.url}", fetch_redirect_response=False
            )
        self.assertEqual(Memory.objects.count(), 0)

    def test_upload_page_can_carry_a_file(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_upload(self):
        response = self.upload(jpeg_file(), caption="Move-in day")
        self.assertRedirects(response, "/places/dorm/")
        memory = Memory.objects.get()
        self.assertEqual(memory.place, self.place)
        self.assertEqual(memory.caption, "Move-in day")
        self.assertTrue(os.path.exists(memory.photo.path))
        self.assertEqual([str(m) for m in get_messages(response.wsgi_request)], ["Photo added."])

    def test_date_filled_from_photo_when_left_empty(self):
        self.upload(jpeg_file(taken=datetime.datetime(2026, 5, 9, 14, 3)))
        self.assertEqual(Memory.objects.get().taken_on, datetime.date(2026, 5, 9))

    def test_typed_date_wins_over_the_photos_date(self):
        self.upload(jpeg_file(taken=datetime.datetime(2026, 5, 9)), taken_on="2026-03-01")
        self.assertEqual(Memory.objects.get().taken_on, datetime.date(2026, 3, 1))

    def test_undated_photo(self):
        response = self.upload(jpeg_file())
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Memory.objects.get().taken_on)

    def test_saved_photo_is_whole(self):
        # Reading the date and checking the format must not eat part of the file.
        photo = jpeg_file(taken=datetime.datetime(2026, 5, 9))
        original = photo.read()
        photo.seek(0)
        self.upload(photo)
        with open(Memory.objects.get().photo.path, "rb") as saved:
            self.assertEqual(saved.read(), original)

    def test_bad_file_saves_nothing(self):
        before = files_on_disk()  # other tests in this class share the folder
        response = self.upload(text_file("notes.jpg"), caption="kept on the form")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "kept on the form")
        self.assertEqual(Memory.objects.count(), 0)
        self.assertEqual(files_on_disk(), before)

    def test_upload_to_other_users_place(self):
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.upload(jpeg_file()).status_code, 404)
        self.assertEqual(Memory.objects.count(), 0)

    def test_awkward_file_names(self):
        # Review focus 3: the phone's name for the file never reaches the disk.
        self.upload(jpeg_file("my room 🏠 (1).JPG"))
        self.upload(jpeg_file("x" * 196 + ".jpg"))
        self.assertEqual(Memory.objects.count(), 2)
        for memory in Memory.objects.all():
            self.assertRegex(memory.photo.name, r"^places/\d+/memories/[0-9a-f]{32}\.jpg$")
