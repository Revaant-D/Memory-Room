"""What the admin site (/admin/) shows for the rooms app."""

from django.contrib import admin

from rooms.models import Memory, Pin, Place, Scan


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "slug", "created"]
    list_filter = ["owner"]
    search_fields = ["name", "slug"]
    # The slug is made by the app, so the admin shows it but cannot edit it.
    readonly_fields = ["slug", "created"]


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    # "id" is the scan's number, which `manage.py import_room` asks for.
    list_display = ["id", "place", "taken_on", "status", "created"]
    list_filter = ["status"]
    readonly_fields = ["created"]


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ["__str__", "place", "taken_on", "created"]
    search_fields = ["caption"]
    readonly_fields = ["created"]


@admin.register(Pin)
class PinAdmin(admin.ModelAdmin):
    list_display = ["memory", "scan", "x", "y", "z", "placed_by", "created"]
    list_filter = ["placed_by"]
    readonly_fields = ["created"]
