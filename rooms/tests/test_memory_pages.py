"""Tests for the photo pages: the grid on a place's page, and a photo's own page
(caption, date, delete). How photos are uploaded is in test_memory_upload.py;
who can fetch a photo file is in test_memory_files.py.
"""

import datetime
import os

from django.contrib.messages import get_messages

from rooms.models import Memory, Pin, Place, Scan
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user, video_file


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


class MemoryPagesTestCase(TempMediaTestCase):
    """Two users. ana owns the place "Dorm" and is logged in."""

    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="Dorm")
        self.client.force_login(self.ana)

    def make_memory(self, place=None, **fields):
        fields.setdefault("photo", jpeg_file())
        return Memory.objects.create(place=place or self.place, **fields)


class PhotoGridTests(MemoryPagesTestCase):
    def test_no_photos_offers_to_add(self):
        # 18 Nov: "No photos yet." went; the "Add photos" link says it.
        response = self.client.get("/places/dorm/")
        self.assertContains(response, 'href="/places/dorm/memories/new/"')

    def test_place_page_shows_photos(self):
        first, second = self.make_memory(), self.make_memory()
        response = self.client.get("/places/dorm/")
        self.assertContains(response, "2 photos")  # 18 Nov: was "Photos (2)"
        self.assertContains(response, f'src="{first.photo_address()}"')
        self.assertContains(response, f'src="{second.photo_address()}"')

    def test_other_users_photos_not_listed(self):
        mine = self.make_memory()
        flat = Place.objects.create(owner=self.ben, name="Flat")
        theirs = self.make_memory(place=flat)
        self.client.force_login(self.ben)
        response = self.client.get("/places/flat/")
        self.assertContains(response, theirs.photo_address())
        self.assertNotContains(response, mine.photo_address())

    def test_caption_and_date_shown(self):
        self.make_memory(caption="Move-in day", taken_on=datetime.date(2026, 5, 9))
        response = self.client.get("/places/dorm/")
        self.assertContains(response, "Move-in day")
        self.assertContains(response, "9 May 2026")

    def test_photo_without_caption_or_date(self):
        # 18 Nov: no "(no caption)" or "no date" filler under each photo.
        self.make_memory()
        response = self.client.get("/places/dorm/")
        self.assertContains(response, 'alt="Photo with no caption"')
        self.assertNotContains(response, "(no caption)")

    def test_newest_photo_first_undated_last(self):
        self.make_memory(caption="undated one")
        self.make_memory(caption="march one", taken_on=datetime.date(2026, 3, 1))
        self.make_memory(caption="may one", taken_on=datetime.date(2026, 5, 9))
        page = self.client.get("/places/dorm/").content.decode()
        self.assertLess(page.index("may one"), page.index("march one"))
        self.assertLess(page.index("march one"), page.index("undated one"))

    def test_each_photo_links_to_its_page(self):
        memory = self.make_memory()
        response = self.client.get("/places/dorm/")
        self.assertContains(response, f'href="/memories/{memory.pk}/edit/"')

    def test_place_page_survives_a_missing_file(self):
        # Review focus 5: the media folder was cleared but the rows remain.
        memory = self.make_memory()
        os.remove(memory.photo.path)
        self.assertEqual(self.client.get("/places/dorm/").status_code, 200)
        self.assertEqual(self.client.get(f"/memories/{memory.pk}/edit/").status_code, 200)


class MemoryEditTests(MemoryPagesTestCase):
    def setUp(self):
        super().setUp()
        self.memory = self.make_memory(caption="First night")
        self.edit = f"/memories/{self.memory.pk}/edit/"
        self.delete = f"/memories/{self.memory.pk}/delete/"

    def test_edit_page_shows_photo(self):
        response = self.client.get(self.edit)
        self.assertContains(response, f'src="{self.memory.photo_address()}"')
        self.assertContains(response, 'value="First night"')

    def test_save_caption(self):
        response = self.client.post(self.edit, {"caption": "Move-in day", "taken_on": ""}, follow=True)
        self.assertRedirects(response, "/places/dorm/")
        self.assertContains(response, "Move-in day")
        self.assertContains(response, "Photo updated.")
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.caption, "Move-in day")

    def test_caption_shown_as_text(self):
        self.client.post(self.edit, {"caption": "<script>alert(1)</script>", "taken_on": ""})
        response = self.client.get("/places/dorm/")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_change_date(self):
        self.client.post(self.edit, {"caption": "", "taken_on": "2026-08-20"})
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.taken_on, datetime.date(2026, 8, 20))

    def test_clear_date(self):
        self.memory.taken_on = datetime.date(2026, 8, 20)
        self.memory.save()
        self.client.post(self.edit, {"caption": "", "taken_on": ""})
        self.memory.refresh_from_db()
        self.assertIsNone(self.memory.taken_on)

    def test_bad_date_is_refused(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=2)
        response = self.client.post(self.edit, {"caption": "x", "taken_on": tomorrow.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.caption, "First night")

    def test_edit_cannot_swap_the_photo_or_the_place(self):
        # Only the caption and the date are on the form, whatever a request adds.
        flat = Place.objects.create(owner=self.ana, name="Flat")
        before = self.memory.photo.name
        self.client.post(
            self.edit, {"caption": "x", "taken_on": "", "place": flat.pk, "photo": jpeg_file()}
        )
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.place, self.place)
        self.assertEqual(self.memory.photo.name, before)

    def test_other_user_cannot_edit(self):
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get(self.edit).status_code, 404)
        response = self.client.post(self.edit, {"caption": "mine now", "taken_on": ""})
        self.assertEqual(response.status_code, 404)
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.caption, "First night")

    def test_delete_asks_first(self):
        response = self.client.get(self.delete)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First night")
        self.assertTrue(Memory.objects.filter(pk=self.memory.pk).exists())

    def test_delete(self):
        path = self.memory.photo.path
        response = self.client.post(self.delete)
        self.assertRedirects(response, "/places/dorm/")
        self.assertFalse(Memory.objects.filter(pk=self.memory.pk).exists())
        self.assertFalse(os.path.exists(path))
        self.assertEqual(message_texts(response), ["Photo deleted."])

    def test_delete_takes_the_photos_pins_and_leaves_the_scan(self):
        scan = Scan.objects.create(place=self.place, video=video_file())
        Pin.objects.create(memory=self.memory, scan=scan, x=1.0, y=1.0, z=1.0, placed_by="user")
        self.client.post(self.delete)
        self.assertEqual(Pin.objects.count(), 0)
        self.assertTrue(Scan.objects.filter(pk=scan.pk).exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get(self.delete).status_code, 404)
        self.assertEqual(self.client.post(self.delete).status_code, 404)
        self.assertTrue(Memory.objects.filter(pk=self.memory.pk).exists())

    def test_edit_delete_need_login(self):
        self.client.logout()
        for path in (self.edit, self.delete):
            for response in (self.client.get(path), self.client.post(path)):
                self.assertRedirects(
                    response, f"/accounts/login/?next={path}", fetch_redirect_response=False
                )
        self.assertTrue(Memory.objects.filter(pk=self.memory.pk).exists())
