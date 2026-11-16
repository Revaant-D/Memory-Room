"""Shows users in Django's admin site, with Django's standard user screens."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User

admin.site.register(User, UserAdmin)
