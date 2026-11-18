"""The owner checks: who may open what.

Every view that needs a place gets it from here, never straight from the
database. That way the rule "each user sees only their own places" is written
in one spot and no view can forget it.
"""

from django.shortcuts import get_object_or_404

from rooms.models import Place


def get_own_place(user, slug):
    """Return this user's place with this address word, or answer 404.

    THIS LINE IS THE PRIVACY RULE FOR THE WHOLE APP. The lookup asks for the
    slug and the owner together, so another user's place is simply not found.
    The answer is the same 404 as for a place that does not exist: nobody can
    tell from the response which addresses are taken by someone else.
    """
    return get_object_or_404(Place, owner=user, slug=slug)
