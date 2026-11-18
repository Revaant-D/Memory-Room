"""Reads the date a photo was taken from inside the photo file.

A camera writes facts about each photo into the file itself (the "Exif"
block): the date and time, the camera model, sometimes the location. This
module reads one of them, the capture date, so a new memory can start with
the right date without the person typing it.
"""

import datetime

from PIL import Image

EXIF_BLOCK = 0x8769  # where the camera's own facts are kept inside the file
DATE_TAKEN = 36867  # "DateTimeOriginal": when the shutter was pressed
DATE_CHANGED = 306  # "DateTime": when the file was last written; a fallback


def photo_taken_on(file):
    """Return the date the photo was taken, or None if it does not say.

    Never raises: a screenshot with no date, a garbled date, or a file that is
    not an image at all gives None. Leaves the file rewound to the start, so
    whoever reads it next gets the whole file.
    """
    try:
        file.seek(0)
        with Image.open(file) as image:
            exif = image.getexif()
            text = exif.get_ifd(EXIF_BLOCK).get(DATE_TAKEN) or exif.get(DATE_CHANGED)
        # Cameras write the date as "2026:05:09 14:03:00".
        moment = datetime.datetime.strptime(str(text).strip()[:19], "%Y:%m:%d %H:%M:%S")
        return moment.date()
    except Exception:  # anything at all that goes wrong means "no date"
        return None
    finally:
        try:
            file.seek(0)
        except Exception:
            pass
