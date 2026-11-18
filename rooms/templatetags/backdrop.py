"""{% backdrop_url place as backdrop %}: the points to draw, faint, behind a page.

A page about a place shows that place's newest built room behind it. A
logged-out page shows the front page's public room, when one is set up.
Anything else gets the plain field.
"""

from django import template
from django.urls import reverse

from rooms.landing import landing_exists
from rooms.models import Place
from rooms.room_page import points_url

register = template.Library()


@register.simple_tag(takes_context=True)
def backdrop_url(context, place=None):
    # A page with no "place" passes an empty string, not None.
    if isinstance(place, Place):
        scan = place.newest_ready_scan()
        return points_url(scan) if scan else ""
    request = context.get("request")
    if request is not None and not request.user.is_authenticated and landing_exists():
        return reverse("landing_points")
    return ""
