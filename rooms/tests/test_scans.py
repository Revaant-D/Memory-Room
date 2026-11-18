"""Tests for room videos: the checks on the file, the form, and the upload and delete pages."""

import datetime
import os

from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from rooms.forms import ScanForm
from rooms.models import Memory, Place, Scan
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user, video_file
from rooms.validators import size_words, validate_video


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def scan_form(video, taken_on=None):
    """A ScanForm as if a person had submitted it with this file and date."""
    data = {"taken_on": (taken_on or timezone.localdate()).isoformat()}
    files = {"video": video} if video is not None else {}
    return ScanForm(data, files)


class ScanFormTests(SimpleTestCase):
    """The form and the video checks. No database is needed to check a file."""

    def test_valid_mp4(self):
        self.assertTrue(scan_form(video_file("room.mp4")).is_valid())

    def test_upper_case_ending(self):
        self.assertTrue(scan_form(video_file("ROOM.MP4")).is_valid())

    def test_mov_accepted(self):
        self.assertTrue(scan_form(video_file("room.mov")).is_valid())

    def test_long_file_name_accepted(self):
        name = "a" * 146 + ".mp4"
        self.assertEqual(len(name), 150)
        self.assertTrue(scan_form(video_file(name)).is_valid())

    def test_wrong_ending(self):
        form = scan_form(SimpleUploadedFile("notes.txt", b"hello"))
        self.assertEqual(form.errors["video"], ["Upload an MP4 or MOV video."])

    def test_wrong_content(self):
        form = scan_form(jpeg_file("room.mp4"))  # a photo with a video's name
        self.assertEqual(form.errors["video"], ["This file is not a video the app can read."])

    @override_settings(MAX_VIDEO_BYTES=10)
    def test_too_large(self):
        form = scan_form(video_file("room.mp4", size=64))
        self.assertIn("too large", form.errors["video"][0])

    def test_size_limit_message_uses_the_setting(self):
        with override_settings(MAX_VIDEO_BYTES=32):
            with self.assertRaisesMessage(ValidationError, "The limit is 32 bytes."):
                validate_video(video_file("room.mp4", size=64))
        self.assertEqual(size_words(500 * 1024 * 1024), "500 MB")

    def test_empty_file(self):
        form = scan_form(SimpleUploadedFile("room.mp4", b""))
        self.assertFalse(form.is_valid())
        self.assertIn("video", form.errors)

    def test_no_file(self):
        form = scan_form(None)
        self.assertEqual(form.errors["video"], ["This field is required."])

    def test_future_date(self):
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        form = scan_form(video_file(), taken_on=tomorrow)
        self.assertEqual(form.errors["taken_on"], ["The date can't be in the future."])

    def test_date_defaults_to_today(self):
        field = ScanForm()["taken_on"]
        self.assertEqual(field.initial, timezone.localdate())
        # The date arrives in the page in the form a date picker understands.
        self.assertIn(f'value="{timezone.localdate().isoformat()}"', str(field))
        self.assertEqual(str(field).count("<input"), 1)

    def test_check_leaves_file_rewound(self):
        video = video_file()
        validate_video(video)
        self.assertEqual(video.tell(), 0)


class ScanPageTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="Dorm")
        self.client.force_login(self.ana)

    def upload(self, video=None, taken_on=None, **kwargs):
        data = {
            "video": video or video_file(),
            "taken_on": (taken_on or timezone.localdate()).isoformat(),
        }
        return self.client.post("/places/dorm/scans/new/", data, **kwargs)

    def make_scan(self, **fields):
        fields.setdefault("video", video_file())
        return Scan.objects.create(place=self.place, **fields)

    def test_pages_need_login(self):
        scan = self.make_scan()
        self.client.logout()
        for path in ("/places/dorm/scans/new/", f"/scans/{scan.pk}/delete/"):
            for response in (self.client.get(path), self.client.post(path)):
                self.assertRedirects(
                    response, f"/accounts/login/?next={path}", fetch_redirect_response=False
                )
        self.assertEqual(Scan.objects.count(), 1)

    def test_upload_page_can_carry_a_file(self):
        response = self.client.get("/places/dorm/scans/new/")
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_upload(self):
        response = self.upload(follow=True)
        self.assertRedirects(response, "/places/dorm/")
        scan = Scan.objects.get()
        self.assertEqual(scan.place, self.place)
        self.assertEqual(scan.status, "uploaded")
        self.assertTrue(os.path.exists(scan.video.path))
        self.assertContains(response, "Its room isn\u2019t built yet.")  # 18 Nov: was "· Uploaded"
        self.assertContains(response, "Room video added.")

    def test_upload_with_date(self):
        response = self.upload(taken_on=datetime.date(2026, 9, 1), follow=True)
        self.assertEqual(Scan.objects.get().taken_on, datetime.date(2026, 9, 1))
        self.assertContains(response, "1 Sep 2026")

    def test_upload_bad_file(self):
        response = self.upload(video=SimpleUploadedFile("notes.txt", b"hello"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Scan.objects.count(), 0)
        self.assertContains(response, "Upload an MP4 or MOV video.")

    def test_upload_to_other_users_place(self):
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get("/places/dorm/scans/new/").status_code, 404)
        self.assertEqual(self.upload().status_code, 404)
        self.assertEqual(Scan.objects.count(), 0)

    def test_two_scans_newest_first(self):
        self.make_scan(taken_on=datetime.date(2026, 9, 1))
        self.make_scan(taken_on=datetime.date(2026, 11, 1))
        page = self.client.get("/places/dorm/").content.decode()
        self.assertLess(page.index("1 Nov 2026"), page.index("1 Sep 2026"))

    def test_delete_asks_first(self):
        scan = self.make_scan()
        response = self.client.get(f"/scans/{scan.pk}/delete/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Scan.objects.filter(pk=scan.pk).exists())

    def test_delete(self):
        scan = self.make_scan()
        photo = Memory.objects.create(place=self.place, photo=jpeg_file())
        path = scan.video.path
        response = self.client.post(f"/scans/{scan.pk}/delete/")
        self.assertRedirects(response, "/places/dorm/")
        self.assertFalse(Scan.objects.filter(pk=scan.pk).exists())
        self.assertFalse(os.path.exists(path))
        self.assertEqual(message_texts(response), ["Room video deleted."])
        # Deleting a video leaves the place and its photos alone.
        self.assertTrue(Memory.objects.filter(pk=photo.pk).exists())

    def test_other_user_cannot_delete(self):
        scan = self.make_scan()
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get(f"/scans/{scan.pk}/delete/").status_code, 404)
        self.assertEqual(self.client.post(f"/scans/{scan.pk}/delete/").status_code, 404)
        self.assertTrue(Scan.objects.filter(pk=scan.pk).exists())

    def test_no_scans_text(self):
        response = self.client.get("/places/dorm/")
        self.assertContains(response, "No room yet.")  # 18 Nov: was "No room video yet."
        self.assertContains(response, 'href="/places/dorm/scans/new/"')
