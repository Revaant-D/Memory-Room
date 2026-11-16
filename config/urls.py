"""The top of the address map.

Every request starts here. Django reads the list from the top and hands the
request to the first entry whose pattern matches the address.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("rooms.urls")),
]
