from django.apps import AppConfig


class RoomsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rooms"

    def ready(self):
        # Importing the module is what connects its functions to Django.
        from rooms import signals  # noqa: F401
