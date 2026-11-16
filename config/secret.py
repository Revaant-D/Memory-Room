"""Where the app's secret key comes from.

Django signs login sessions and form tokens with a secret key. Anyone who has
the key can forge them, so the key must never be in git.

The key is looked for in this order:

1. The DJANGO_SECRET_KEY environment variable. A deployed site sets this.
2. A file named .secret_key next to manage.py. It is listed in .gitignore.
3. If neither exists, a new random key is made and saved to that file.

Step 3 is why a fresh clone runs with no set-up.

This module uses only Python's standard library, plus one Django exception
class. It is imported while the settings are still loading, so it must not
touch anything that needs the settings.
"""

import os
import secrets
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

ENV_VAR = "DJANGO_SECRET_KEY"
KEY_FILE_NAME = ".secret_key"


def load_secret_key(base_dir: Path) -> str:
    """Return the secret key, creating and saving one if none exists yet."""
    from_env = os.environ.get(ENV_VAR, "").strip()
    if from_env:
        return from_env

    key_file = Path(base_dir) / KEY_FILE_NAME
    try:
        # "utf-8-sig" reads plain UTF-8 and also drops the invisible mark that
        # Notepad and PowerShell 5 put at the start of a file.
        saved = key_file.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        saved = ""
    except (OSError, UnicodeError) as error:
        raise ImproperlyConfigured(
            f"Could not read the secret key file {key_file}: {error}. "
            f"Fix the file, or set the {ENV_VAR} environment variable."
        ) from error
    if saved:
        return saved

    # No key anywhere (or the file was blank): make one and save it.
    new_key = secrets.token_urlsafe(50)
    try:
        key_file.write_text(new_key, encoding="utf-8")
    except OSError as error:
        raise ImproperlyConfigured(
            f"Could not save a new secret key to {key_file}: {error}. "
            f"Make the folder writable, or set the {ENV_VAR} environment variable."
        ) from error
    try:
        # Only the owner may read it. This does nothing on Windows.
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return new_key
