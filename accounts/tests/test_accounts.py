"""Tests for accounts: the user model, sign-up, login and logout."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

PASSWORD = "pass-12345-word"


def session_user_id(client):
    """The id of the user this test browser is logged in as, or None."""
    return client.session.get("_auth_user_id")


class UserModelTests(TestCase):
    def test_user_model_is_ours(self):
        self.assertEqual(get_user_model()._meta.label, "accounts.User")

    def test_password_is_stored_hashed(self):
        user = get_user_model().objects.create_user("ana", password=PASSWORD)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertNotIn(PASSWORD, user.password)
        self.assertTrue(user.check_password(PASSWORD))


class AddressTests(TestCase):
    def test_addresses(self):
        self.assertEqual(reverse("signup"), "/accounts/signup/")
        self.assertEqual(reverse("login"), "/accounts/login/")
        self.assertEqual(reverse("logout"), "/accounts/logout/")


class SignupTests(TestCase):
    def signup(self, **changes):
        data = {"username": "ana", "password1": PASSWORD, "password2": PASSWORD}
        data.update(changes)
        return self.client.post("/accounts/signup/", data)

    def test_signup_page_loads(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_signup_creates_user_and_logs_in(self):
        response = self.signup()
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user = get_user_model().objects.get(username="ana")
        self.assertEqual(session_user_id(self.client), str(user.pk))

    def test_signup_gives_an_ordinary_account(self):
        # Nobody may become staff or a superuser through the sign-up form,
        # whatever extra fields they add to the request.
        self.signup(is_staff="on", is_superuser="on")
        user = get_user_model().objects.get(username="ana")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_signup_welcomes_the_user(self):
        response = self.client.post(
            "/accounts/signup/",
            {"username": "ana", "password1": PASSWORD, "password2": PASSWORD},
            follow=True,
        )
        self.assertContains(response, "Welcome, ana.")

    def test_signup_password_mismatch(self):
        response = self.signup(password2="something-else-99")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())
        self.assertIn("password2", response.context["form"].errors)
        self.assertIsNone(session_user_id(self.client))

    def test_signup_duplicate_username(self):
        get_user_model().objects.create_user("ana", password=PASSWORD)
        response = self.signup()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.filter(username="ana").count(), 1)
        self.assertIn("username", response.context["form"].errors)

    def test_signup_username_differing_only_in_case(self):
        # "Ana" and "ana" would be confusingly similar accounts.
        get_user_model().objects.create_user("ana", password=PASSWORD)
        response = self.signup(username="Ana")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_signup_weak_password(self):
        response = self.signup(password1="12345678", password2="12345678")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_blank_username(self):
        response = self.signup(username="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_refuses_html_in_username(self):
        response = self.signup(username="<b>ana</b>")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_errors_are_shown(self):
        response = self.signup(password2="something-else-99")
        self.assertContains(response, "errorlist")

    def test_signup_does_not_echo_the_password(self):
        response = self.signup(password2="something-else-99")
        self.assertNotContains(response, PASSWORD)

    def test_logged_in_user_skips_signup(self):
        get_user_model().objects.create_user("ana", password=PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        response = self.client.get("/accounts/signup/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("ana", password=PASSWORD)

    def login(self, **changes):
        data = {"username": "ana", "password": PASSWORD}
        data.update(changes)
        return self.client.post("/accounts/login/", data)

    def test_login_page_loads(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_login_ok(self):
        response = self.login()
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(session_user_id(self.client), str(self.user.pk))

    def test_login_wrong_password(self):
        response = self.login(password="not-the-password")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(session_user_id(self.client))
        self.assertContains(response, "errorlist")

    def test_login_unknown_user(self):
        response = self.login(username="nobody")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(session_user_id(self.client))

    def test_login_returns_to_the_page_asked_for(self):
        response = self.client.post(
            "/accounts/login/?next=/accounts/signup/",
            {"username": "ana", "password": PASSWORD},
        )
        self.assertRedirects(
            response, "/accounts/signup/", fetch_redirect_response=False
        )

    def test_login_will_not_redirect_to_another_site(self):
        response = self.client.post(
            "/accounts/login/?next=https://evil.example/",
            {"username": "ana", "password": PASSWORD},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_logged_in_user_skips_login(self):
        self.client.login(username="ana", password=PASSWORD)
        response = self.client.get("/accounts/login/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)


class LogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("ana", password=PASSWORD)

    def setUp(self):
        self.client.login(username="ana", password=PASSWORD)

    def test_logout_is_post_only(self):
        response = self.client.get("/accounts/logout/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(session_user_id(self.client), str(self.user.pk))

    def test_logout(self):
        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertIsNone(session_user_id(self.client))


def header_html(response):
    """Only the page header, so a test is not fooled by links in the page body."""
    page = response.content.decode()
    start = page.index("<header")
    end = page.index("</header>")
    return page[start:end]


class HeaderTests(TestCase):
    def test_header_logged_out(self):
        # 18 Nov (Dollhouse look): logged out, the header is the wordmark only; the
        # front page's own buttons carry "Sign up" and "Log in", so they are not said twice.
        response = self.client.get("/")
        self.assertContains(response, 'href="/accounts/login/"')
        self.assertContains(response, 'href="/accounts/signup/"')
        self.assertNotIn("Log out", header_html(response))

    def test_header_logged_in(self):
        get_user_model().objects.create_user("ana", password=PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        # follow=True because chunk 3 makes "/" redirect a logged-in user.
        header = header_html(self.client.get("/", follow=True))
        self.assertIn("ana", header)
        self.assertIn("Log out", header)
        self.assertNotIn('href="/accounts/signup/"', header)
        self.assertNotIn('href="/accounts/login/"', header)

    def test_logout_button_is_a_post_form_with_a_token(self):
        get_user_model().objects.create_user("ana", password=PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        header = header_html(self.client.get("/", follow=True))
        self.assertIn('action="/accounts/logout/"', header)
        self.assertIn('method="post"', header)
        self.assertIn("csrfmiddlewaretoken", header)

    def test_username_is_shown_as_text(self):
        # The sign-up form refuses < and > in a username, but a username can
        # reach the database another way (the admin, a script). The header
        # must show whatever it is given as text, never as HTML.
        get_user_model().objects.create_user("<b>ana</b>", password=PASSWORD)
        self.client.login(username="<b>ana</b>", password=PASSWORD)
        header = header_html(self.client.get("/", follow=True))
        self.assertIn("&lt;b&gt;ana&lt;/b&gt;", header)
        self.assertNotIn("<b>ana</b>", header)
