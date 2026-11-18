"""Checks on uploaded files, run before anything is saved.

A validator is a function that takes the uploaded file and either returns
quietly or raises ValidationError with the message the person will see.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image

VIDEO_ENDINGS = (".mp4", ".mov")
PHOTO_FORMATS = {"JPEG", "PNG", "WEBP"}
# The ending a stored photo gets, from the format found inside it.
PHOTO_ENDINGS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def size_words(number_of_bytes):
    """500 * 1024 * 1024 -> "500 MB". Used in messages about size limits."""
    megabytes = number_of_bytes / (1024 * 1024)
    if megabytes >= 1:
        return f"{megabytes:.0f} MB" if megabytes == int(megabytes) else f"{megabytes:.1f} MB"
    return f"{number_of_bytes} bytes"


def validate_video(file):
    """Accept an MP4 or MOV room video; refuse anything else.

    Three checks, cheapest first:

    1. The file name ends in .mp4 or .mov (any case).
    2. The file is no larger than settings.MAX_VIDEO_BYTES.
    3. The file itself starts the way MP4 and MOV files do: bytes 4 to 8 are
       the letters "ftyp". A file's name is whatever the sender says it is;
       its first bytes are harder to get wrong by accident. This is a quick
       sanity check, not proof that the video will play.
    """
    name = (file.name or "").lower()
    if not name.endswith(VIDEO_ENDINGS):
        raise ValidationError("Upload an MP4 or MOV video.")

    if file.size > settings.MAX_VIDEO_BYTES:
        limit = size_words(settings.MAX_VIDEO_BYTES)
        raise ValidationError(f"This video is too large. The limit is {limit}.")

    try:
        file.seek(0)
        start = file.read(12)
    finally:
        file.seek(0)  # leave the file rewound for whoever reads it next
    if start[4:8] != b"ftyp":
        raise ValidationError("This file is not a video the app can read.")


def validate_photo(file):
    """Accept a JPEG, PNG or WebP photo; refuse anything else.

    Two checks:

    1. The file is no larger than settings.MAX_PHOTO_BYTES.
    2. Pillow, the image library, can open the file and says it is one of the
       three formats. The file's name is not looked at: the content decides.

    An iPhone's HEIC photo fails the second check, because Pillow cannot open
    HEIC, and gets a message that says so instead of an error page.

    Returns the format Pillow found ("JPEG", "PNG" or "WEBP"), so the caller
    can name the stored file by its content (PHOTO_ENDINGS), never by the
    name the browser sent.
    """
    if file.size > settings.MAX_PHOTO_BYTES:
        limit = size_words(settings.MAX_PHOTO_BYTES)
        raise ValidationError(f"This photo is too large. The limit is {limit}.")

    try:
        file.seek(0)
        with Image.open(file) as image:  # reads only the start of the file
            kind = image.format
    except Exception:  # not an image Pillow knows
        kind = None
    finally:
        file.seek(0)  # leave the file rewound for whoever reads it next
    if kind not in PHOTO_FORMATS:
        raise ValidationError("Upload JPEG, PNG or WebP photos. HEIC is not supported yet.")
    return kind
