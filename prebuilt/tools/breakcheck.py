"""Proves the kits' tests can fail: breaks the code on purpose and checks a test notices.

    .venv\\Scripts\\python.exe prebuilt\\tools\\breakcheck.py

`kit.py verify` shows the tests pass. That alone does not show the tests are
any good: a test that checks nothing also passes. This script makes a
temporary copy of the project with every kit laid on top, then, one at a
time, breaks one rule in the copy (removes the owner check, stops deleting
files, and so on), runs the whole test suite, and expects it to FAIL. Then it
puts the line back. The real project and the kits are never touched.

"caught" means at least one test failed, as it should. "MISSED" means the
suite still passed with the rule broken: the tests have a hole there.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit  # noqa: E402

# (file, the line as it is, the line broken, what was broken)
CASES = [
    (
        "rooms/access.py",
        "get_object_or_404(Place, owner=user, slug=slug)",
        "get_object_or_404(Place, slug=slug)",
        "anyone can open any place (owner check removed)",
    ),
    (
        "rooms/access.py",
        "get_object_or_404(Scan, pk=pk, place__owner=user)",
        "get_object_or_404(Scan, pk=pk)",
        "anyone can delete any room video",
    ),
    (
        "rooms/views.py",
        "            form.instance.owner = request.user\n",
        "            form.instance.owner_id = request.POST.get('owner') or request.user.pk\n",
        "a request can create a place in someone else's name",
    ),
    (
        "rooms/models.py",
        "        self.full_clean()\n",
        "",
        "pins are saved without checking their rules",
    ),
    (
        "rooms/signals.py",
        "        instance.photo.delete(save=False)",
        "        pass",
        "a deleted photo's file stays on disk",
    ),
    (
        "rooms/slugs.py",
        'RESERVED = {"new"}',
        "RESERVED = set()",
        'a place named "New" takes over the create page\'s address',
    ),
    (
        "rooms/slugs.py",
        "    while slug in RESERVED or slug in taken:",
        "    while slug in RESERVED:",
        "two places of one owner can get the same address",
    ),
    (
        "rooms/validators.py",
        '    if start[4:8] != b"ftyp":',
        "    if False:",
        "a photo renamed .mp4 is accepted as a video",
    ),
    (
        "rooms/validators.py",
        "    if file.size > settings.MAX_VIDEO_BYTES:",
        "    if False:",
        "the video size limit is ignored",
    ),
    (
        "rooms/validators.py",
        "    if kind not in PHOTO_FORMATS:",
        "    if False:",
        "any file is accepted as a photo",
    ),
    (
        "rooms/photos.py",
        "        return moment.date()",
        "        return None",
        "a photo's date is never read",
    ),
    (
        "rooms/forms.py",
        "        if taken_on > timezone.localdate():",
        "        if False:",
        "a room video can be dated in the future",
    ),
]

# Extra breaks tried only when a chunk 5 version is laid on top with --choice.
# A line that a version does not have is skipped quietly (the four versions differ).
CHOICE_CASES = [
    (
        "rooms/access.py",
        "get_object_or_404(Memory, pk=pk, place__owner=user)",
        "get_object_or_404(Memory, pk=pk)",
        "anyone can open, edit or delete any photo",
    ),
    (
        "rooms/views.py",
        "        memory.delete()  # rooms/signals.py removes the file from disk\n",
        "        pass\n",
        "deleting a photo does nothing",
    ),
    (
        "rooms/views.py",
        "                        taken_on=photo_taken_on(photo),  # None when the photo has no date\n",
        "",
        "an uploaded photo's own date is not used (many-at-once version)",
    ),
    (
        "rooms/views.py",
        "                form.instance.taken_on = photo_taken_on(form.cleaned_data[\"photo\"])\n",
        "                pass\n",
        "an uploaded photo's own date is not used (one-per-form version)",
    ),
    (
        "rooms/forms.py",
        "                validate_photo(file)  # ours: size, and really a JPEG, PNG or WebP\n",
        "",
        "any file is accepted in a batch of photos (many-at-once version)",
    ),
    (
        "rooms/forms.py",
        "        if len(files) > most:",
        "        if False:",
        "the limit on photos per upload is ignored (many-at-once version)",
    ),
    (
        "rooms/views.py",
        '    response["Cache-Control"] = "private, max-age=3600"\n',
        "",
        "a shared cache may keep a private photo (owner-checked version)",
    ),
]


def main():
    choice = None
    if len(sys.argv) == 3 and sys.argv[1] == "--choice":
        choice = kit.find_kit(sys.argv[2])
    elif len(sys.argv) > 1:
        sys.exit("usage: breakcheck.py [--choice NAME]")
    cases = [(*case, False) for case in CASES]
    if choice is not None:
        cases += [(*case, True) for case in CHOICE_CASES]
    work = Path(tempfile.mkdtemp(prefix="memory-room-breakcheck-"))
    try:
        for rel in kit.tracked_files():
            if not rel.startswith(("docs/", ".idea/", "prebuilt/")) and (kit.PROJECT / rel).is_file():
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(kit.PROJECT / rel, work / rel)
        for k in kit.KITS:
            kit.copy_kit(k, work)
        if choice is not None:
            kit.copy_kit(choice, work)
            print(f"With {choice['name']} on top.")

        def suite_passes():
            return subprocess.run(
                [sys.executable, "manage.py", "test"], cwd=work, capture_output=True
            ).returncode == 0

        if not suite_passes():
            sys.exit("The suite fails before anything is broken. Run kit.py verify first.")
        print("Unbroken: the suite passes. Now breaking one thing at a time.\n")

        missed = 0
        tried = 0
        for rel, good, bad, what, skip_if_absent in cases:
            path = work / rel
            original = path.read_text(encoding="utf-8")
            if skip_if_absent and good not in original:
                continue
            tried += 1
            if original.count(good) != 1:
                print(f"  SKIPPED  {what}  (the line to break was not found once in {rel})")
                missed += 1
                continue
            path.write_text(original.replace(good, bad), encoding="utf-8", newline="\n")
            caught = not suite_passes()
            path.write_text(original, encoding="utf-8", newline="\n")
            print(f"  {'caught ' if caught else 'MISSED '}  {what}")
            missed += 0 if caught else 1

        print(f"\n{tried - missed} of {tried} breaks were caught by the tests.")
        if missed:
            sys.exit(1)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
