"""The user.

This is Django's own user, unchanged: a username, a hashed password, and the
staff and superuser flags. It is declared here, in our code, rather than used
straight from Django, for one reason: every other table points at the user
table, and Django makes it very hard to swap the user class once real accounts
exist. Owning the class from the start means a field can be added later (a
display name, say) with an ordinary migration.

The setting AUTH_USER_MODEL = "accounts.User" tells Django to use this class.
Other code never imports it directly: models use settings.AUTH_USER_MODEL and
everything else calls get_user_model().
"""

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
