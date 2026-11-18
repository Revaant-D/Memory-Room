"""The forms of the rooms app. A form checks what a person typed before it is saved."""

from django import forms

from rooms.models import Place


class PlaceForm(forms.ModelForm):
    """Create or rename a place. The one thing a person types is its name.

    The owner is not a field: the view sets it from whoever is logged in, so
    nobody can create a place in someone else's name. The slug is not a field
    either: Place.save() makes it.
    """

    class Meta:
        model = Place
        fields = ["name"]
