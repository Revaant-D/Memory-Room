"""Tests for the home page and the page frame every page shares."""

from django.contrib.staticfiles import finders
from django.test import TestCase


class HomeTests(TestCase):
    def test_home_shows_landing(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Memory Room")
        self.assertContains(response, "Sign up")
        self.assertContains(response, "Log in")

    def test_home_is_named(self):
        from django.urls import reverse

        self.assertEqual(reverse("home"), "/")

    def test_page_frame_fits_a_phone(self):
        # Without this tag a phone shows the page zoomed out, as if on a desktop.
        response = self.client.get("/")
        self.assertContains(response, 'name="viewport"')

    def test_page_links_the_stylesheet(self):
        response = self.client.get("/")
        self.assertContains(response, "css/site.css")

    def test_stylesheet_exists(self):
        self.assertIsNotNone(finders.find("css/site.css"))

    def test_unknown_address_is_a_404(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)


class ErrorPageTests(TestCase):
    def test_not_found_page_is_ours(self):
        # The same page a person sees when they open another user's place.
        response = self.client.get("/no-such-page/")
        self.assertContains(response, "Page not found", status_code=404)
        self.assertContains(response, 'href="/"', status_code=404)
        self.assertContains(response, "css/site.css", status_code=404)

    def test_not_found_page_does_not_repeat_the_address(self):
        # Echoing the address back would let a crafted link put text on our page.
        response = self.client.get("/no-such-page-marker-123/")
        self.assertNotContains(response, "marker-123", status_code=404)

    def test_server_error_page_stands_alone(self):
        # Django draws this page with no request and no user, at a moment when
        # something is already broken. It must not need base.html or any data.
        from django.template.loader import get_template

        template = get_template("500.html")
        self.assertIn("Something went wrong", template.render())
        source = template.template.source
        self.assertNotIn("{%", source)  # no tags: nothing to extend, load or look up
        self.assertNotIn("{{", source)  # no variables
