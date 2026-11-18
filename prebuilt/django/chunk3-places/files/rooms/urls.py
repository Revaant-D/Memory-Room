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
]
