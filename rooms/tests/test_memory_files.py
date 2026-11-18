"""Tests for who can fetch a photo file: only its owner, through a view (decision D3, option a)."""

import os

from rooms.models import Memory, Place
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user


class PhotoFileTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.place = Place.objects.create(owner=self.ana, name="Dorm")
        photo = jpeg_file()
        self.original = photo.read()
        photo.seek(0)
        self.memory = Memory.objects.create(place=self.place, photo=photo)
        self.url = f"/memories/{self.memory.pk}/photo/"
        self.client.force_login(self.ana)

    def fetch(self, url=None):
        """GET a photo; return (response, body). Closes the file the response holds open."""
        response = self.client.get(url or self.url)
        body = b""
        if response.status_code == 200:
            body = b"".join(response.streaming_content)
        response.close()
        return response, body

    def test_photo_address_is_the_view(self):
        self.assertEqual(self.memory.photo_address(), self.url)

    def test_photo_served_to_owner(self):
        response, body = self.fetch()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(body, self.original)

    def test_a_file_with_another_ending_is_never_served_as_a_page(self):
        # Review, 18 Nov: the type came from the stored ending. A row whose file
        # ends ".html" (put in through the shell or the admin) must not become a page.
        memory = Memory.objects.create(place=self.place, photo=jpeg_file("evil.html"))
        response, _ = self.fetch(f"/memories/{memory.pk}/photo/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")

    def test_photo_may_be_kept_only_by_the_owners_browser(self):
        response, _ = self.fetch()
        self.assertEqual(response["Cache-Control"], "private, max-age=3600")

    def test_photo_needs_login(self):
        self.client.logout()
        response, _ = self.fetch()
        self.assertRedirects(
            response, f"/accounts/login/?next={self.url}", fetch_redirect_response=False
        )

    def test_photo_refused_to_others(self):
        self.client.force_login(self.ben)
        response, _ = self.fetch()
        self.assertEqual(response.status_code, 404)

    def test_unknown_photo(self):
        response, _ = self.fetch("/memories/999999/photo/")
        self.assertEqual(response.status_code, 404)

    def test_photo_file_missing(self):
        # Review focus 5: the row exists but the file has gone from disk.
        os.remove(self.memory.photo.path)
        response, _ = self.fetch()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/places/dorm/").status_code, 200)

    def test_media_folder_not_public(self):
        # The stored path is not an address. Nothing answers under /media/.
        response, _ = self.fetch(f"/media/{self.memory.photo.name}")
        self.assertEqual(response.status_code, 404)
        self.client.logout()
        response, _ = self.fetch(f"/media/{self.memory.photo.name}")
        self.assertEqual(response.status_code, 404)
