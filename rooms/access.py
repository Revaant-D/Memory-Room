"""The owner checks: who may open what.

Every view that needs a place gets it from here, never straight from the
database. That way the rule "each user sees only their own places" is written
in one spot and no view can forget it.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404

from rooms.models import Memory, Place, Scan


def get_own_place(user, slug):
    """Return this user's place with this address word, or answer 404.

    THIS LINE IS THE PRIVACY RULE FOR THE WHOLE APP. The lookup asks for the
    slug and the owner together, so another user's place is simply not found.
    The answer is the same 404 as for a place that does not exist: nobody can
    tell from the response which addresses are taken by someone else.
    """
    return get_object_or_404(Place, owner=user, slug=slug)


def get_own_scan(user, pk):
    """Return this user's scan with this id, or answer 404.

    A scan has no owner of its own. It belongs to a place, and the place has
    the owner, so the lookup follows that link: place__owner=user.
    """
    return get_object_or_404(Scan, pk=pk, place__owner=user)


def get_own_memory(user, pk):
    """Return this user's memory (photo) with this id, or answer 404.

    Like a scan, a memory belongs to a place and the place has the owner.
    """
    return get_object_or_404(Memory, pk=pk, place__owner=user)


def get_own_built_scan(user, pk):
    """This user's scan, if its 3D room has been built; otherwise 404."""
    scan = get_own_scan(user, pk)
    if scan.status != Scan.Status.READY or not scan.points_file:
        raise Http404("This room has not been built yet.")
    return scan
