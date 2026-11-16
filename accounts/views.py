"""The sign-up page. Login and logout use Django's own views; see urls.py."""

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from accounts.forms import SignupForm


@sensitive_post_parameters("password1", "password2")  # keep passwords out of error reports
@never_cache  # a browser must not keep a copy of this page
def signup(request):
    """Create an account and log the new user in."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()  # the password is hashed here
            login(request, user)  # starts the session: a database row and a cookie
            messages.success(request, f"Welcome, {user.get_username()}.")
            return redirect("home")
    else:
        form = SignupForm()

    # A first visit, or a form with errors to show.
    return render(request, "registration/signup.html", {"form": form})
