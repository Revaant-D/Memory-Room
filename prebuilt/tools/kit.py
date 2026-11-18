"""Check, verify and apply the prebuilt Django kits.

Run it with the project's own Python, from the project folder:

    .venv\\Scripts\\python.exe prebuilt\\tools\\kit.py status
    .venv\\Scripts\\python.exe prebuilt\\tools\\kit.py verify
    .venv\\Scripts\\python.exe prebuilt\\tools\\kit.py apply chunk2-models
    .venv\\Scripts\\python.exe prebuilt\\tools\\kit.py apply chunk2-models --write

What the commands do:

    status   For every kit, says whether its files are already in the project,
             ready to go in, or blocked because the project file they replace
             is no longer the one the kit was built against.
    verify   Copies the project to a temporary folder, lays the kits on top in
             order, and runs the checks and the whole test suite there. The
             real project is not touched. Use --upto NAME to stop after a kit.
             Use --choice NAME to add one of the four chunk 5 versions on top.
             Add --keep to leave the copy in place and run its server by hand.
    apply    Copies one kit's files into the project. Without --write it only
             prints what it would do. It never commits and never migrates.
    plan-tests   Checks that every test the build plan names for chunks 2 to 4
             exists in a kit.

See also tools/breakcheck.py, which breaks the code on purpose to prove the
tests notice.

A kit is a folder with a `files/` tree that mirrors the project's own layout,
and a `manifest.json` that says, for each file, whether it is new or replaces
a project file, and the fingerprint of the file it expects to replace.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PREBUILT = Path(__file__).resolve().parent.parent
PROJECT = PREBUILT.parent
_CONFIG = json.loads((PREBUILT / "kits.json").read_text(encoding="utf-8"))
# KITS go in one after another, in this order.
KITS = _CONFIG["django"]
# CHOICES are four versions of the rest of chunk 5, one per answer to D2 and D3.
# Exactly one of them goes in, on top of all of KITS, after the builder decides.
CHOICES = _CONFIG.get("chunk5_choices", [])


def fingerprint(path):
    """A hash of the file's contents that ignores Windows/Unix line endings."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def kit_root(kit):
    return PREBUILT / kit["dir"] / "files"


def kit_files(kit):
    root = kit_root(kit)
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def manifest(kit):
    path = PREBUILT / kit["dir"] / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))["files"]


def find_kit(name):
    for kit in KITS + CHOICES:
        if kit["name"] == name:
            return kit
    names = ", ".join(k["name"] for k in KITS + CHOICES)
    sys.exit(f"No kit called {name!r}. The kits are: {names}")


def later_kits(kit):
    """The kits that go in after this one and may replace its files again."""
    if kit in KITS:
        return KITS[KITS.index(kit) + 1 :] + CHOICES
    return []


def file_state(kit, rel, target_root):
    """One of: 'applied', 'ready', 'conflict'."""
    entry = manifest(kit)[rel]
    target = target_root / rel
    if target.exists():
        # The file counts as applied if it is this kit's version, or the
        # version of a later kit that built on top of this one.
        versions = [kit_root(kit) / rel]
        versions += [kit_root(k) / rel for k in later_kits(kit) if (kit_root(k) / rel).is_file()]
        if fingerprint(target) in {fingerprint(v) for v in versions}:
            return "applied"
    if entry["action"] == "add":
        return "conflict" if target.exists() else "ready"
    if target.exists() and fingerprint(target) == entry["base"]:
        return "ready"
    return "conflict"


def own_files_applied(kit, target_root):
    """True when every file of this kit is in the project exactly as the kit has it."""
    return all(
        (target_root / rel).exists()
        and fingerprint(target_root / rel) == fingerprint(kit_root(kit) / rel)
        for rel in kit_files(kit)
    )


def kit_states(kit, target_root):
    return {rel: file_state(kit, rel, target_root) for rel in kit_files(kit)}


def copy_kit(kit, target_root):
    for rel in kit_files(kit):
        target = target_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(kit_root(kit) / rel, target)


# --- commands ---------------------------------------------------------------


def cmd_status(args):
    earlier_all_applied = True
    for kit in KITS:
        states = kit_states(kit, PROJECT)
        values = list(states.values())
        if all(v == "applied" for v in values):
            word = "APPLIED"
        elif not earlier_all_applied:
            word = "WAITING"  # an earlier kit goes in first; nothing is wrong
        elif "conflict" in values:
            word = "BLOCKED"
        elif all(v in ("ready", "applied") for v in values) and "ready" in values:
            word = "READY" if "applied" not in values else "PARTLY APPLIED"
        else:
            word = "?"
        print(f"{kit['name']:<18} {word:<15} {len(values)} files   {kit['title']}")
        if word in ("BLOCKED", "PARTLY APPLIED"):
            for rel, state in states.items():
                if state != "applied":
                    print(f"    {state:<9} {rel}")
        earlier_all_applied = earlier_all_applied and word == "APPLIED"
    if CHOICES:
        print()
        print("The rest of chunk 5. Apply exactly ONE, after the builder answers D2 and D3:")
        chosen = [c["name"] for c in CHOICES if own_files_applied(c, PROJECT)]
        for choice in CHOICES:
            values = list(kit_states(choice, PROJECT).values())
            if choice["name"] in chosen:
                word = "APPLIED"
            elif chosen:
                word = "NOT CHOSEN"
            elif not earlier_all_applied:
                word = "WAITING"
            elif "conflict" in values:
                word = "BLOCKED"
            else:
                word = "READY"
            print(f"{choice['name']:<18} {word:<15} {len(values)} files   {choice['title']}")
    print()
    print("Kits go in order, top to bottom. WAITING: an earlier kit goes in first.")
    print("BLOCKED: a project file was edited after the kit was built against it;")
    print("the files listed need merging by hand (see the kit's README).")


def cmd_apply(args):
    kit = find_kit(args.name)
    states = kit_states(kit, PROJECT)
    files = manifest(kit)
    for rel, state in states.items():
        print(f"  {state:<9} {files[rel]['action']:<8} {rel}")
    conflicts = [rel for rel, state in states.items() if state == "conflict"]
    if conflicts:
        print()
        print("Nothing was copied. The files marked 'conflict' differ from what this")
        print("kit was built against. Either an earlier kit is not applied, or the")
        print("project changed. Merge those files by hand; see the kit's README.")
        sys.exit(1)
    if not args.write:
        print()
        print("Dry run: nothing was copied. Add --write to copy the files.")
        return
    copy_kit(kit, PROJECT)
    print()
    print(f"Copied {len(states)} files into {PROJECT}.")
    print("Next, from the project folder:")
    print("  .venv\\Scripts\\python.exe manage.py migrate")
    print("  .venv\\Scripts\\python.exe manage.py test")
    print(f"Then do the walk-through and the record step in {kit['dir']}/README.md.")


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=PROJECT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [name for name in out.split("\0") if name]


def run(label, command, cwd):
    print(f"\n--- {label}: {' '.join(command[1:])}", flush=True)
    result = subprocess.run([sys.executable, *command[1:]], cwd=cwd)
    return result.returncode == 0


def cmd_verify(args):
    names = [k["name"] for k in KITS]
    upto = args.upto or names[-1]
    if upto not in names:
        sys.exit(f"--upto takes one of: {', '.join(names)}. For a chunk 5 version use --choice.")
    choice = find_kit(args.choice) if args.choice else None
    if choice is not None and (choice not in CHOICES or args.upto):
        sys.exit("--choice takes one of the chunk 5 versions, and cannot be combined with --upto.")
    work = Path(tempfile.mkdtemp(prefix="memory-room-verify-"))
    try:
        for rel in tracked_files():
            if rel.startswith(("docs/", ".idea/", "prebuilt/")):
                continue
            source = PROJECT / rel
            if source.is_file():
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, work / rel)
        applied = []
        for kit in KITS:
            copy_kit(kit, work)
            applied.append(kit["name"])
            if kit["name"] == upto:
                break
        if choice is not None:
            copy_kit(choice, work)
            applied.append(choice["name"])
        print(f"Temporary copy: {work}")
        print(f"Kits laid on top: {', '.join(applied)}", flush=True)
        results = {
            "check": run("check", ["python", "manage.py", "check"], work),
            "migrations match the models": run(
                "migrations",
                ["python", "manage.py", "makemigrations", "--check", "--dry-run"],
                work,
            ),
            "tests": run("tests", ["python", "manage.py", "test"], work),
        }
        leftover = (work / "media").exists()
        print("\n=== Result")
        for label, ok in results.items():
            print(f"  {'ok    ' if ok else 'FAILED'} {label}")
        print(f"  {'FAILED' if leftover else 'ok    '} tests left no files in media/")
        if args.keep:
            print(f"\nKept: {work}")
            print("To click through the pages without touching the real project:")
            print(f'  cd "{work}"')
            print(f'  & "{sys.executable}" manage.py migrate')
            print(f'  & "{sys.executable}" manage.py runserver 8001')
            print("Delete the folder when done.")
        if not all(results.values()) or leftover:
            sys.exit(1)
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)


def cmd_plan_tests(args):
    """Is every test the build plan names for chunks 2 to 4 present in a kit?"""
    import re

    plan = (PROJECT / "docs/plans/2026-11-16-django-foundation.md").read_text(encoding="utf-8")
    part = plan[plan.index("# Chunk 2: The four models") : plan.index("# Chunk 5: Photos")]
    wanted = re.findall(r"^(test_\w+)", part, flags=re.M)
    have = set()
    for path in (PREBUILT / "django").rglob("test_*.py"):
        have |= set(re.findall(r"def (test_\w+)", path.read_text(encoding="utf-8")))
    missing = [name for name in wanted if name not in have]
    print(f"The plan names {len(wanted)} tests for chunks 2, 3 and 4.")
    print(f"{len(wanted) - len(missing)} are in the kits. Missing: {missing or 'none'}")
    print(f"The kits' test files hold {len(have)} different test names; the ones the plan")
    print("does not name are listed in each kit's README.")
    print("This checks names only. Whether each test checks what its name says is")
    print("for a reader (and tools/breakcheck.py) to judge.")
    if missing:
        sys.exit(1)


def cmd_rebuild_manifests(args):
    """For whoever edits a kit. Only correct while NO kit is applied to the project."""
    state = {}
    for rel in tracked_files():
        if (PROJECT / rel).is_file():
            state[rel] = fingerprint(PROJECT / rel)
    for kit in KITS:
        files = {}
        for rel in kit_files(kit):
            if rel in state:
                files[rel] = {"action": "replace", "base": state[rel]}
            else:
                files[rel] = {"action": "add", "base": None}
            state[rel] = fingerprint(kit_root(kit) / rel)
        path = PREBUILT / kit["dir"] / "manifest.json"
        path.write_text(json.dumps({"files": files}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(PROJECT)} ({len(files)} files)")
    # Each chunk 5 version is built against the project with every kit above applied.
    for choice in CHOICES:
        files = {}
        for rel in kit_files(choice):
            if rel in state:
                files[rel] = {"action": "replace", "base": state[rel]}
            else:
                files[rel] = {"action": "add", "base": None}
        path = PREBUILT / choice["dir"] / "manifest.json"
        path.write_text(json.dumps({"files": files}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(PROJECT)} ({len(files)} files)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    p = sub.add_parser("apply")
    p.add_argument("name")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_apply)
    p = sub.add_parser("verify")
    p.add_argument("--upto")
    p.add_argument("--choice", help="also lay one chunk 5 version on top of all the kits")
    p.add_argument("--keep", action="store_true", help="leave the temporary copy in place")
    p.set_defaults(func=cmd_verify)
    sub.add_parser("plan-tests").set_defaults(func=cmd_plan_tests)
    sub.add_parser("rebuild-manifests").set_defaults(func=cmd_rebuild_manifests)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
