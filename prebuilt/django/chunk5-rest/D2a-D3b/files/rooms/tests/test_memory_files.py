"""Tests for who can fetch a photo file: anyone who has its address (decision D3, option b).

These tests record what option b means, including the part that is a
trade-off: a photo's address works without logging in.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.test import RequestFactory, override_settings

from rooms.models import Memory, Place
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user


class PhotoFileTests(TempMediaTestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.place = Place.objects.create(owner=self.ana, name="Dorm")
        photo = jpeg_file()
        self.original = photo.read()
        photo.seek(0)
        self.memory = Memory.objects.create(place=self.place, photo=photo)

    def test_photo_address_is_the_files_own_address(self):
        self.assertEqual(self.memory.photo_address(), f"/media/{self.memory.photo.name}")
        self.assertRegex(self.memory.photo_address(), r"^/media/places/\d+/memories/[0-9a-f]{32}\.jpg$")

    def test_there_is_no_photo_view(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(f"/memories/{self.memory.pk}/photo/").status_code, 404)

    def test_media_is_not_served_when_debug_is_off(self):
        # Tests always run with DEBUG off, like a deployed site. Django's own
        # file serving is for development only; a deployed site needs its web
        # server or a storage bucket to answer /media/.
        self.assertFalse(settings.DEBUG)
        self.assertEqual(self.client.get(self.memory.photo_address()).status_code, 404)

    def test_with_debug_on_anyone_with_the_address_gets_the_photo(self):
        # What config/urls.py adds while DEBUG is on, called here directly.
        with override_settings(DEBUG=True):
            (pattern,) = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        request = RequestFactory().get(self.memory.photo_address())  # nobody is logged in
        response = pattern.callback(request, path=self.memory.photo.name, **pattern.default_args)
        body = b"".join(response.streaming_content)
        response.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body, self.original)

    def test_top_address_map_serves_media(self):
        import inspect

        import config.urls

        self.assertIn("static(settings.MEDIA_URL", inspect.getsource(config.urls))
