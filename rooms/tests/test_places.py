"""Tests for the places pages: list, create, open, rename, delete, and who may do so."""

from django.contrib.messages import get_messages
from django.core.files.base import ContentFile

from rooms.models import Memory, Place, Scan
from rooms.tests.utils import TempMediaTestCase, jpeg_file, make_user, video_file


def message_texts(response):
    """The one-time messages ("Place created.") a response is carrying."""
    return [str(m) for m in get_messages(response.wsgi_request)]


class PlacePagesTestCase(TempMediaTestCase):
    """Two users. ana is logged in unless a test says otherwise."""

    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.client.force_login(self.ana)

    def make_place(self, name="Dorm Room", owner=None):
        return Place.objects.create(owner=owner or self.ana, name=name)


class PlaceListCreateOpenTests(PlacePagesTestCase):
    def test_pages_need_login(self):
        self.client.logout()
        for path in ("/places/", "/places/new/", "/places/x/"):
            response = self.client.get(path)
            self.assertRedirects(
                response, f"/accounts/login/?next={path}", fetch_redirect_response=False
            )

    def test_list_shows_only_mine(self):
        self.make_place("Dorm")
        self.make_place("Flat", owner=self.ben)
        response = self.client.get("/places/")
        self.assertContains(response, "Dorm")
        self.assertNotContains(response, "Flat")

    def test_empty_list(self):
        # 18 Nov (Dollhouse look): was "No places yet"; the empty field offers the first place.
        response = self.client.get("/places/")
        self.assertContains(response, "Film your first place")
        self.assertContains(response, 'href="/places/new/"')

    def test_create_place(self):
        response = self.client.post("/places/new/", {"name": "Dorm Room 214"}, follow=True)
        self.assertRedirects(response, "/places/dorm-room-214/")
        place = Place.objects.get()
        self.assertEqual(place.owner, self.ana)
        self.assertEqual(place.name, "Dorm Room 214")
        self.assertContains(response, "Dorm Room 214")
        self.assertContains(response, "Place created.")

    def test_create_ignores_an_owner_in_the_request(self):
        # The owner is whoever is logged in, whatever the request claims.
        self.client.post("/places/new/", {"name": "Dorm", "owner": self.ben.pk})
        self.assertEqual(Place.objects.get().owner, self.ana)

    def test_create_blank_name(self):
        response = self.client.post("/places/new/", {"name": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Place.objects.count(), 0)
        self.assertIn("name", response.context["form"].errors)

    def test_create_long_name(self):
        response = self.client.post("/places/new/", {"name": "x" * 81})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Place.objects.count(), 0)

    def test_open_other_users_place(self):
        self.make_place("Dorm")
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get("/places/dorm/").status_code, 404)

    def test_same_slug_two_owners(self):
        self.make_place("Dorm Room")
        self.make_place("Dorm Room", owner=self.ben)
        self.assertEqual(self.client.get("/places/dorm-room/").context["place"].owner, self.ana)
        self.client.force_login(self.ben)
        self.assertEqual(self.client.get("/places/dorm-room/").context["place"].owner, self.ben)

    def test_name_shown_as_text(self):
        place = self.make_place("<b>x</b>")
        response = self.client.get(place.get_absolute_url())
        self.assertContains(response, "&lt;b&gt;x&lt;/b&gt;")
        self.assertNotContains(response, "<b>x</b>")

    def test_place_named_new_opens(self):
        # Review focus 1: "New" must not collide with the create page.
        place = self.make_place("New")
        self.assertEqual(place.get_absolute_url(), "/places/new-2/")
        self.assertContains(self.client.get("/places/new-2/"), "New")
        self.assertContains(self.client.get("/places/new/"), "Create place")

    def test_detail_offers_a_video_and_photos(self):
        # 18 Nov: the "Room scans" and "Photos" headings went with the Dollhouse look.
        place = self.make_place()
        response = self.client.get(place.get_absolute_url())
        self.assertContains(response, f'href="/places/{place.slug}/scans/new/"')
        self.assertContains(response, f'href="/places/{place.slug}/memories/new/"')


class PlaceRenameDeleteTests(PlacePagesTestCase):
    def setUp(self):
        super().setUp()
        self.place = self.make_place("Dorm Room")

    def test_rename(self):
        response = self.client.post("/places/dorm-room/edit/", {"name": "Old Dorm"})
        self.assertRedirects(response, "/places/dorm-room/")
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, "Old Dorm")
        self.assertEqual(self.place.slug, "dorm-room")
        self.assertEqual(message_texts(response), ["Place renamed."])

    def test_rename_blank(self):
        response = self.client.post("/places/dorm-room/edit/", {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, "Dorm Room")

    def test_delete_asks_first(self):
        response = self.client.get("/places/dorm-room/delete/")
        self.assertContains(response, "Dorm Room")
        self.assertTrue(Place.objects.filter(pk=self.place.pk).exists())

    def test_delete(self):
        response = self.client.post("/places/dorm-room/delete/")
        self.assertRedirects(response, "/places/")
        self.assertFalse(Place.objects.filter(pk=self.place.pk).exists())
        self.assertEqual(message_texts(response), ["Place deleted."])

    def test_delete_page_counts(self):
        Scan.objects.create(place=self.place, video=video_file())
        Memory.objects.create(place=self.place, photo=jpeg_file())
        Memory.objects.create(place=self.place, photo=jpeg_file())
        response = self.client.get("/places/dorm-room/delete/")
        self.assertContains(response, "1 room video")
        self.assertNotContains(response, "1 room videos")
        self.assertContains(response, "2 photos")

    def test_other_user_cannot_rename(self):
        self.client.force_login(self.ben)
        response = self.client.post("/places/dorm-room/edit/", {"name": "Mine now"})
        self.assertEqual(response.status_code, 404)
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, "Dorm Room")

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.ben)
        response = self.client.post("/places/dorm-room/delete/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Place.objects.filter(pk=self.place.pk).exists())

    def test_edit_delete_need_login(self):
        self.client.logout()
        for path in ("/places/dorm-room/edit/", "/places/dorm-room/delete/"):
            for response in (self.client.get(path), self.client.post(path)):
                self.assertRedirects(
                    response, f"/accounts/login/?next={path}", fetch_redirect_response=False
                )
        self.assertTrue(Place.objects.filter(pk=self.place.pk).exists())


class PlaceListRoomsTests(PlacePagesTestCase):
    """Your places (18 Nov): a place with a built room is drawn as its model; the rest are plots."""

    PLY = b"ply\nformat binary_little_endian 1.0\nelement vertex 0\nend_header\n"

    def place_with_room(self, name):
        place = self.make_place(name)
        scan = Scan.objects.create(place=place, video=video_file())
        scan.points_file.save("points.ply", ContentFile(self.PLY), save=False)
        scan.status = Scan.Status.READY
        scan.save()
        return place, scan

    def test_place_with_a_room_is_drawn_as_its_model(self):
        place, scan = self.place_with_room("Octave Room")
        Memory.objects.create(place=place, photo=jpeg_file())
        response = self.client.get("/places/")
        self.assertContains(response, f"/scans/{scan.pk}/points.ply?v=")
        self.assertContains(response, 'class="model"')
        self.assertContains(response, "1 photo")

    def test_place_without_a_room_is_a_plot(self):
        self.make_place("Kitchen")
        response = self.client.get("/places/")
        self.assertContains(response, "Kitchen")
        self.assertContains(response, "No room yet")
        self.assertNotContains(response, "points.ply")

    def test_at_most_three_models(self):
        for name in ("One", "Two", "Three", "Four"):
            self.place_with_room(name)
        response = self.client.get("/places/")
        self.assertEqual(response.content.decode().count("points.ply?v="), 3)
        for name in ("One", "Two", "Three", "Four"):
            self.assertContains(response, name)  # the fourth is still there, as a plot
