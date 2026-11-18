"""The forms of the rooms app. A form checks what a person typed before it is saved."""

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
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


# --- Adding photos ----------------------------------------------------------
#
# Django's file field takes one file. These two small classes make one that
# takes many, following "Uploading multiple files" in the Django 5.2
# documentation.


class MultipleFileInput(forms.ClearableFileInput):
    """A file input that lets a person pick several files at once."""

    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    """A form field whose value is a list of checked photo files.

    Every file is checked. If any fails, the whole upload is refused and the
    message names each bad file, so the person knows which one to leave out.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget", MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"})
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # One file arrives as itself, several as a list, none as None or [].
        if not data:
            files = []
        elif isinstance(data, (list, tuple)):
            files = list(data)
        else:
            files = [data]

        if not files:
            super().clean(None, initial)  # raises "This field is required."
            return []

        most = settings.MAX_PHOTOS_PER_UPLOAD
        if len(files) > most:
            raise ValidationError(f"Upload at most {most} photos at a time.")

        problems = []
        for file in files:
            try:
                super().clean(file, initial)  # Django's own checks: not empty, has a name
                validate_photo(file)  # ours: size, and really a JPEG, PNG or WebP
            except ValidationError as error:
                problems.extend(f"{file.name}: {message}" for message in error.messages)
        if problems:
            raise ValidationError(problems)
        return files


class MemoryUploadForm(forms.Form):
    """Add photos to a place: one field, many files.

    Not a ModelForm, because one submission makes many Memory rows. The view
    creates them. Captions and dates are added afterwards, photo by photo.
    """

    photos = MultipleImageField(label="Photos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The numbers come from the settings, so the text cannot drift from the rule.
        self.fields["photos"].help_text = (
            f"JPEG, PNG or WebP. Up to {settings.MAX_PHOTOS_PER_UPLOAD} at a time, "
            f"{size_words(settings.MAX_PHOTO_BYTES)} each."
        )
