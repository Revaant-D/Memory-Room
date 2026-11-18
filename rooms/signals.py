"""Removes uploaded files from disk when their database rows are deleted.

Django deletes the row but leaves the file, on purpose. Without this, deleting
a photo would leave the photo on disk for good. These two functions run after
every delete of a Scan or a Memory, including the deletes that happen because
a whole Place (or a whole user) was deleted.

They are connected to Django in rooms/apps.py.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from rooms.models import Memory, Scan


@receiver(post_delete, sender=Scan)
def delete_scan_files(sender, instance, **kwargs):
    for field in (instance.video, instance.points_file):
        if field:  # an empty field has no file to remove
            field.delete(save=False)  # save=False: the row is already gone


@receiver(post_delete, sender=Memory)
def delete_memory_file(sender, instance, **kwargs):
    if instance.photo:
        instance.photo.delete(save=False)
