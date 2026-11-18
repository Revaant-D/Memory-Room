"""The forms of the rooms app. A form checks what a person typed before it is saved."""

from django import forms
from django.conf import settings
from django.utils import timezone

from rooms.models import Memory, Place, Scan
from rooms.validators import size_words, validate_photo, validate_video


class PlaceForm(forms.ModelForm):
    """Create or rename a place. The one thing a person types is its name.

    The owner is not a field: the view sets it from whoever is logged in, so
    nobody can create a place in someone else's name. The slug is not a field
    either: Place.save() makes it.
    """

    class Meta:
        model = Place
        fields = ["name"]


class ScanForm(forms.ModelForm):
    """Add a room video to a place.

    The place is not a field: the view takes it from the address. The status
    is not a field either: a new scan always starts as "uploaded".
    """

    # Declared here instead of letting Django build it from the model. The
    # built one refuses any file whose original name is longer than 100
    # characters, and the original name is never stored (see models.py).
    video = forms.FileField(
        label="Room video",
        validators=[validate_video],
        widget=forms.ClearableFileInput(attrs={"accept": "video/mp4,video/quicktime"}),
        help_text="Film at 1080p. One to two minutes is enough. MP4 or MOV.",
    )

    class Meta:
        model = Scan
        fields = ["video", "taken_on"]
        labels = {"taken_on": "Filmed on"}
        widgets = {
            # type="date" gives the phone's own date picker.
            "taken_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The date starts as today because the model says so (Scan.taken_on's
        # default). For a default like that, Django also adds a second, hidden
        # copy of the input to the page. Nothing here uses it, so it is off.
        self.fields["taken_on"].show_hidden_initial = False

    def clean_taken_on(self):
        taken_on = self.cleaned_data["taken_on"]
        if taken_on > timezone.localdate():
            raise forms.ValidationError("The date can't be in the future.")
        return taken_on


class MemoryForm(forms.ModelForm):
    """Change a photo's caption and date. Both may be left empty.

    The photo itself is not a field: this form edits a memory that already
    has its photo.
    """

    class Meta:
        model = Memory
        fields = ["caption", "taken_on"]
        labels = {"taken_on": "Taken on"}
        widgets = {
            "taken_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_taken_on(self):
        taken_on = self.cleaned_data["taken_on"]  # None when left empty
        if taken_on and taken_on > timezone.localdate():
            raise forms.ValidationError("The date can't be in the future.")
        return taken_on


# --- Adding a photo ---------------------------------------------------------


class MemoryUploadForm(forms.ModelForm):
    """Add one photo to a place, with its caption and date on the same form.

    The place is not a field: the view takes it from the address.
    """

    # Declared here for the same reason as ScanForm.video: the field Django
    # would build refuses a file whose original name is over 100 characters,
    # and the original name is never stored.
    photo = forms.FileField(
        label="Photo",
        validators=[validate_photo],
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )

    class Meta:
        model = Memory
        fields = ["photo", "caption", "taken_on"]
        labels = {"taken_on": "Taken on"}
        help_texts = {"taken_on": "Leave empty to use the date inside the photo, if it has one."}
        widgets = {
            "taken_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The number comes from the settings, so the text cannot drift from the rule.
        self.fields["photo"].help_text = (
            f"JPEG, PNG or WebP, up to {size_words(settings.MAX_PHOTO_BYTES)}."
        )

    def clean_taken_on(self):
        taken_on = self.cleaned_data["taken_on"]  # None when left empty
        if taken_on and taken_on > timezone.localdate():
            raise forms.ValidationError("The date can't be in the future.")
        return taken_on
