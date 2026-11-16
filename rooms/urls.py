"""Addresses for the rooms app. Each line maps one address to one view function."""

from django.urls import path

from rooms import views

urlpatterns = [
    path("", views.home, name="home"),
]
