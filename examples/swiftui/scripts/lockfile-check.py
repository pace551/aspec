#!/usr/bin/env python3
"""lockfile-check.py — SEC-SUPPLY-02 for SwiftPM: everything `swift package resolve` pins
is pinned the same way in the Package.resolved committed to git (run by the CI typecheck
job).

sca and license-audit can only check what Package.resolved pins, so a dependency that
resolve pins but the committed lockfile doesn't would skip both. That covers a missing
lockfile, a gitignored one, a stale one, and remote packages reached through a local
`.package(path:)` dependency. Pins compare whole (identity, kind, location, state), so a
moved or forked source counts as a change. The committed copy is read from git's index,
not the working tree: `swift build` may already have rewritten the file there. A newer
toolchain rewriting only the file's format (same pins) passes.

For an SPM package (needs Package.swift). Exit 0 = nothing to pin, or the committed
lockfile matches; 1 = not committed, or stale; 2 = swift or git failed. Runs on the
project's python3 (3.9+), standard library only.
"""

import json
import subprocess  # nosec B404 - fixed argv (swift, git), no shell
import sys
from pathlib import Path

LOCK = Path("Package.resolved")


class Failed(Exception):
    pass


def run(*argv):
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # nosec B603
    if proc.returncode != 0:
        raise Failed(f"{' '.join(argv)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def pins(text):
    """The pins of a Package.resolved, comparable across format versions 2 and 3."""
    data = json.loads(text)
    raw = data["object"]["pins"] if data.get("version") == 1 else data["pins"]
    return sorted(json.dumps(p, sort_keys=True) for p in raw)


def main():
    try:
        run("swift", "package", "resolve")
        if not LOCK.is_file() or not pins(LOCK.read_text(encoding="utf-8")):
            print("lockfile-check: swift package resolve pins nothing, so no lockfile needed")
            return 0
        resolved = pins(LOCK.read_text(encoding="utf-8"))
        tracked = subprocess.run(  # nosec B603 B607 - fixed argv
            ["git", "ls-files", "--error-unmatch", "--", str(LOCK)],
            capture_output=True,
            text=True,
            check=False,
        )
        if tracked.returncode == 1:
            print(
                f"lockfile-check: FAIL — swift package resolve pins {len(resolved)} "
                "package(s) but Package.resolved is not tracked by git (missing, untracked "
                "or gitignored): commit it (SEC-SUPPLY-02)"
            )
            return 1
        if tracked.returncode != 0:
            raise Failed(f"git ls-files: {tracked.stderr.strip()}")
        committed = pins(run("git", "show", f":{LOCK}"))
    except (Failed, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"lockfile-check: {exc}", file=sys.stderr)
        return 2
    if committed != resolved:
        print(
            "lockfile-check: FAIL — the committed Package.resolved is stale: swift package "
            "resolve pins differently; commit the resolved file"
        )
        return 1
    print(f"lockfile-check: committed Package.resolved is current ({len(resolved)} pins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
