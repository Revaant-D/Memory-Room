"""The top of the address map.

Every request starts here. Django reads the list from the top and hands the
request to the first entry whose pattern matches the address.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("rooms.urls")),
]

# Uploaded photos are fetched straight from the media/ folder, at /media/...
# static() adds that address only while DEBUG is on: Django's own file serving
# is for development. A deployed site must have its web server or a storage
# bucket answer /media/ instead.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
