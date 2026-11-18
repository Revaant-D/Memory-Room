"""Addresses for the rooms app. Each line maps one address to one view function."""

from django.urls import path

from rooms import views

urlpatterns = [
    path("", views.home, name="home"),
    path("places/", views.place_list, name="place_list"),
    # "new" must come before <slug>: Django takes the first line that matches,
    # and "new" would otherwise be read as a place's address word.
    path("places/new/", views.place_create, name="place_create"),
    path("places/<slug:slug>/", views.place_detail, name="place_detail"),
    path("places/<slug:slug>/edit/", views.place_edit, name="place_edit"),
    path("places/<slug:slug>/delete/", views.place_delete, name="place_delete"),
    # A scan is added to a place, so that address starts with the place.
    # Once it exists it is found by its own number.
    path("places/<slug:slug>/scans/new/", views.scan_create, name="scan_create"),
    path("scans/<int:pk>/delete/", views.scan_delete, name="scan_delete"),
    # Photos ("memories") follow the same pattern as scans.
    path("places/<slug:slug>/memories/new/", views.memory_create, name="memory_create"),
    path("memories/<int:pk>/edit/", views.memory_edit, name="memory_edit"),
    path("memories/<int:pk>/delete/", views.memory_delete, name="memory_delete"),
]
