"""Makes the address word (the "slug") for a place.

A place called "Dorm Room 214" lives at /places/dorm-room-214/. The last part
is the slug. It is made once, when the place is created, and never changes
after that, so a link to a place keeps working when the place is renamed.
"""

from django.utils.text import slugify

# Words that cannot be a place's address because a page already lives there:
# /places/new/ is the "create a place" page.
RESERVED = {"new"}

# The slug column holds 80 characters. The word is cut to 70 so there is
# always room for a number on the end ("-2", "-3", ...).
MAX_WORD = 70

# Used when a name has no letters or digits to build a word from (emoji, or
# a script slugify cannot turn into plain letters).
FALLBACK = "place"


def unique_slug(owner, name):
    """Return an address word for `name` that this owner is not using yet.

    "Dorm Room" gives "dorm-room". If the owner already has that one, the
    answer is "dorm-room-2", then "dorm-room-3", and so on. Two different
    owners can both have "dorm-room"; each only ever sees their own.
    """
    from rooms.models import Place  # imported here because models.py imports this file

    word = slugify(name)[:MAX_WORD].strip("-") or FALLBACK

    taken = set(
        Place.objects.filter(owner=owner, slug__startswith=word).values_list("slug", flat=True)
    )
    slug = word
    number = 2
    while slug in RESERVED or slug in taken:
        slug = f"{word}-{number}"
        number += 1
    return slug
