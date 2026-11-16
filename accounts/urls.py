"""Addresses for accounts. All of them start with /accounts/ (see config/urls.py)."""

from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    # Django's own login view. It uses templates/registration/login.html.
    # A person who is already logged in is sent on instead of shown the form.
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    # Django's own logout view. It answers only to POST, so a link or an image
    # on another site cannot log a person out.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
