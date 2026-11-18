"""Settings for Memory Room.

Everything Django needs to know about this project is in this one file.
Settings reference: https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
import sys
from pathlib import Path

from config.secret import load_secret_key

# The project folder: the one that holds manage.py.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Security -------------------------------------------------------------

# Never written in this file. See config/secret.py for where it comes from.
SECRET_KEY = load_secret_key(BASE_DIR)

# Debug mode shows detailed error pages. It is on unless DJANGO_DEBUG is set
# to something other than "1". A deployed site must set DJANGO_DEBUG=0.
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# The host names this site answers to, comma-separated in DJANGO_ALLOWED_HOSTS.
# While DEBUG is on, Django accepts localhost without listing it here.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]


# --- Apps -----------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # This project's own apps
    "accounts",  # the user, sign-up, login, logout
    "rooms",  # places, scans, memories, pins
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # templates/ holds base.html, the frame every page shares.
        # Each app's own pages are in its own templates/ folder (APP_DIRS).
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database -------------------------------------------------------------

# SQLite: the whole database is the one file db.sqlite3 (git-ignored).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Accounts -------------------------------------------------------------

# Use our own user class (accounts/models.py) instead of Django's stock one.
# This must be set before the first migration and cannot easily change after.
AUTH_USER_MODEL = "accounts.User"

# The rules a new password must pass.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# These are URL names, defined in accounts/urls.py and rooms/urls.py.
LOGIN_URL = "login"  # where a logged-out visitor to a protected page is sent
LOGIN_REDIRECT_URL = "home"  # where a person lands after logging in
LOGOUT_REDIRECT_URL = "home"  # and after logging out

# Real passwords are hashed slowly on purpose, so that a stolen database is
# hard to crack. Tests create many users and do not need that protection, so
# while tests run a fast hasher is used instead. Nothing else differs in tests.
if "test" in sys.argv[1:2]:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# --- Language and time ----------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True  # times are stored in UTC and shown in TIME_ZONE


# --- Files ----------------------------------------------------------------

# Static files are the site's own CSS. They live in static/.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files are what users upload: room videos and photos. They are saved
# under media/ (git-ignored). Nothing serves /media/ addresses: uploads are
# private, so each one is handed out by a view that checks the owner first.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"


# --- Upload limits --------------------------------------------------------

# The largest room video the app accepts. A phone filming at 1080p writes
# roughly 130 MB a minute, so 500 MB is about three minutes of video.
# rooms/validators.py reads this number; the message a person sees uses it too.
MAX_VIDEO_BYTES = 500 * 1024 * 1024

# The largest single photo the app accepts. Phone photos are 2 to 12 MB.
MAX_PHOTO_BYTES = 20 * 1024 * 1024

# The most photos accepted in one upload.
MAX_PHOTOS_PER_UPLOAD = 50
