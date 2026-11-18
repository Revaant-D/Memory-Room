"""Pack the code the Colab notebook needs into one zip: ai/dist/memory-room-ai.zip.

    python ai/pack_for_colab.py

The zip holds roompipe/ and roomgeom/ (no tests, no caches) and PACKED.txt,
which records when it was packed, the git commit it came from, whether ai/
had changes not yet committed, and a fingerprint of every file. The notebook
prints PACKED.txt, so a run's results can be traced to the exact code.

Only the Python standard library is used, so any Python can run this.
"""

import hashlib
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

AI = Path(__file__).resolve().parent
OUT = AI / "dist" / "memory-room-ai.zip"
PACKAGES = ("roompipe", "roomgeom")


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=AI, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main():
    files = sorted(
        p for package in PACKAGES for p in (AI / package).rglob("*.py") if "__pycache__" not in p.parts
    )
    commit = git("rev-parse", "--short", "HEAD") or "unknown"
    changed = "yes" if git("status", "--porcelain", "--", ".") else "no"
    lines = [
        f"packed {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} from commit {commit}; "
        f"uncommitted changes in ai/: {changed}",
    ]
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        lines.append(f"{digest}  {path.relative_to(AI).as_posix()}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(AI).as_posix())
        archive.writestr("PACKED.txt", "\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(files)} files, {OUT.stat().st_size / 1000:.0f} KB)")
    print(lines[0])


if __name__ == "__main__":
    main()
