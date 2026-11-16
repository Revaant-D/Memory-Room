"""The sign-up form."""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    """Asks for a username and a password, typed twice.

    Django's UserCreationForm does the work: it checks the two passwords
    match, runs the password rules from settings.AUTH_PASSWORD_VALIDATORS,
    refuses a username that is taken (ignoring upper and lower case), and
    stores the password hashed. All this class adds is which user model to
    create and which fields to ask for.
    """

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        # Only the username comes from the request. A field left out of this
        # list (is_staff, is_superuser) cannot be set by whoever fills the form.
        fields = ("username",)
