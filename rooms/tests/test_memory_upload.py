"""Tests for adding photos: many at once, captions afterwards (decision D2, option a)."""

import datetime
import io
import os

from django.conf import settings
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from PIL import Image

from rooms.forms import MemoryUploadForm
from rooms.models import Memory, Place
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user


def upload_form(*files):
    """A MemoryUploadForm as if a person had picked these files."""
    return MemoryUploadForm({}, MultiValueDict({"photos": list(files)}))


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
        form = upload_form(jpeg_file())
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data["photos"]), 1)

    def test_three_photos_valid(self):
        form = upload_form(jpeg_file("a.jpg"), jpeg_file("b.jpg"), jpeg_file("c.jpg"))
        self.assertTrue(form.is_valid())
        self.assertEqual([f.name for f in form.cleaned_data["photos"]], ["a.jpg", "b.jpg", "c.jpg"])

    def test_text_file_named_jpg(self):
        form = upload_form(text_file("notes.jpg"))
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors["photos"][0].startswith("notes.jpg: "))

    def test_one_bad_in_three(self):
        form = upload_form(jpeg_file("a.jpg"), text_file("notes.jpg"), jpeg_file("c.jpg"))
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors["photos"]), 1)
        self.assertIn("notes.jpg", form.errors["photos"][0])
        self.assertNotIn("a.jpg", form.errors["photos"][0])

    def test_two_bad_files_are_both_named(self):
        form = upload_form(text_file("one.jpg"), jpeg_file("ok.jpg"), gif_file("two.gif"))
        self.assertEqual(len(form.errors["photos"]), 2)

    def test_gif_refused(self):
        form = upload_form(gif_file())
        self.assertEqual(
            form.errors["photos"],
            ["photo.gif: Upload JPEG, PNG or WebP photos. HEIC is not supported yet."],
        )

    def test_heic_refused(self):
        heic = SimpleUploadedFile("IMG_0001.heic", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64)
        form = upload_form(heic)
        self.assertFalse(form.is_valid())
        self.assertIn("HEIC is not supported yet", form.errors["photos"][0])

    def test_empty_file_refused(self):
        form = upload_form(SimpleUploadedFile("empty.jpg", b""))
        self.assertFalse(form.is_valid())
        self.assertIn("empty.jpg", form.errors["photos"][0])

    @override_settings(MAX_PHOTO_BYTES=10)
    def test_too_large(self):
        form = upload_form(jpeg_file())
        self.assertIn("too large", form.errors["photos"][0])

    @override_settings(MAX_PHOTOS_PER_UPLOAD=2)
    def test_too_many(self):
        form = upload_form(jpeg_file(), jpeg_file(), jpeg_file())
        self.assertEqual(form.errors["photos"], ["Upload at most 2 photos at a time."])

    def test_no_files(self):
        self.assertEqual(MemoryUploadForm({}, {}).errors["photos"], ["This field is required."])
        self.assertEqual(upload_form().errors["photos"], ["This field is required."])

    def test_input_lets_a_person_pick_several(self):
        html = str(MemoryUploadForm()["photos"])
        self.assertIn("multiple", html)
        self.assertIn('accept="image/jpeg,image/png,image/webp"', html)

    def test_help_text_states_the_limits(self):
        self.assertIn("Up to 50 at a time, 20 MB each", MemoryUploadForm()["photos"].help_text)


class MemoryUploadPageTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="Dorm")
        self.client.force_login(self.ana)
        self.url = "/places/dorm/memories/new/"

    def upload(self, *files, **kwargs):
        return self.client.post(self.url, {"photos": list(files)}, **kwargs)

    def test_page_needs_login(self):
        self.client.logout()
        for response in (self.client.get(self.url), self.upload(jpeg_file())):
            self.assertRedirects(
                response, f"/accounts/login/?next={self.url}", fetch_redirect_response=False
            )
        self.assertEqual(Memory.objects.count(), 0)

    def test_stored_ending_follows_the_content(self):
        # Review, 18 Nov: the ending came from the name the browser sent, so a
        # JPEG named "evil.html" was stored as .html and served as a web page.
        self.upload(jpeg_file("evil.html"))
        self.assertTrue(Memory.objects.get().photo.name.endswith(".jpg"))

    def test_png_named_jpg_is_stored_as_png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8)).save(buffer, "PNG")
        self.upload(SimpleUploadedFile("photo.jpg", buffer.getvalue(), content_type="image/jpeg"))
        self.assertTrue(Memory.objects.get().photo.name.endswith(".png"))

    def test_future_date_inside_a_photo_is_not_kept(self):
        # Review, 18 Nov: a camera clock set ahead gave a date the edit page then refused.
        ahead = timezone.localdate() + datetime.timedelta(days=3)
        self.upload(jpeg_file(taken=datetime.datetime.combine(ahead, datetime.time(12, 0))))
        memory = Memory.objects.get()
        self.assertIsNone(memory.taken_on)
        response = self.client.post(f"/memories/{memory.pk}/edit/", {"caption": "Move-in day", "taken_on": ""})
        self.assertEqual(response.status_code, 302)

    def test_upload_page_can_carry_files(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_upload_one(self):
        response = self.upload(jpeg_file())
        self.assertRedirects(response, "/places/dorm/")
        memory = Memory.objects.get()
        self.assertEqual(memory.place, self.place)
        self.assertTrue(os.path.exists(memory.photo.path))
        self.assertEqual([str(m) for m in get_messages(response.wsgi_request)], ["1 photo added."])

    def test_upload_three(self):
        before = files_on_disk()  # other tests in this class share the folder
        response = self.upload(jpeg_file("a.jpg"), jpeg_file("b.jpg"), jpeg_file("c.jpg"))
        self.assertEqual(Memory.objects.count(), 3)
        self.assertEqual(files_on_disk() - before, 3)
        self.assertEqual([str(m) for m in get_messages(response.wsgi_request)], ["3 photos added."])

    def test_date_filled_from_photo(self):
        self.upload(jpeg_file(taken=datetime.datetime(2026, 5, 9, 14, 3)))
        self.assertEqual(Memory.objects.get().taken_on, datetime.date(2026, 5, 9))

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

    def test_bad_batch_saves_nothing(self):
        before = files_on_disk()
        response = self.upload(jpeg_file("a.jpg"), text_file("notes.jpg"), jpeg_file("c.jpg"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "notes.jpg")
        self.assertEqual(Memory.objects.count(), 0)
        self.assertEqual(files_on_disk(), before)  # no new files either

    def test_upload_to_other_users_place(self):
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.upload(jpeg_file()).status_code, 404)
        self.assertEqual(Memory.objects.count(), 0)

    def test_awkward_file_names(self):
        # Review focus 3: the phone's name for the file never reaches the disk.
        self.upload(jpeg_file("my room 🏠 (1).JPG"), jpeg_file("x" * 196 + ".jpg"))
        self.assertEqual(Memory.objects.count(), 2)
        for memory in Memory.objects.all():
            self.assertRegex(memory.photo.name, r"^places/\d+/memories/[0-9a-f]{32}\.jpg$")
