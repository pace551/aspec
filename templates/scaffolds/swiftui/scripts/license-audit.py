#!/usr/bin/env python3
"""license-audit.py — LEG-LICENSING-01 for SwiftPM (the T4 CI job `license-audit`).

No tool reports SwiftPM licenses: deps.dev, which osv-scanner --licenses uses, has no
SwiftPM data. So the review is recorded by hand, per source and version. Every
dependency pinned in a Package.resolved needs a line in licenses.allow,
`<location> <version> <SPDX id>` (the pin's repository URL; host case, a trailing
slash and `.git` don't matter, path case does), naming the license a person checked,
and the license must be on
LEG-LICENSING's allowlist. A new dependency, a new version (a relicense usually comes
with one) or a move to a fork fails until someone reviews it.

Lockfiles: ./Package.resolved (a package) and the ones Xcode keeps under
*.xcodeproj/ and *.xcworkspace/ (an app). That remote dependencies have a committed,
current lockfile at all is scripts/lockfile-check.py's job (the typecheck CI job).

Exit 0 = every pin reviewed and allowed, or no lockfile (no pinned dependencies);
1 = a pin unreviewed or not allowed; 2 = a file can't be read or parsed.
Runs on the project's own python3 (3.9+), standard library only.
"""

import json
import sys
from pathlib import Path

ALLOWED = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC"}  # LEG-LICENSING
XCODE_LOCKFILES = (
    "*.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
    "*.xcworkspace/xcshareddata/swiftpm/Package.resolved",
)


class Unreadable(Exception):
    pass


def lockfiles(root):
    found = [root / "Package.resolved"] if (root / "Package.resolved").is_file() else []
    for pattern in XCODE_LOCKFILES:
        found += sorted(root.glob(pattern))
    return found


def source(url):
    """A repository URL normalized for matching: scheme and host lowercased (they're
    case-insensitive), no trailing / or .git. The path keeps its case: many git hosts
    treat /team/Widget and /team/widget as different repositories."""
    url = url.strip().rstrip("/")
    url = (url[: -len(".git")] if url.endswith(".git") else url).rstrip("/")
    scheme, sep, rest = url.partition("://")
    if not sep:  # scp-style git@host:path
        host, colon, path = url.partition(":")
        return host.lower() + colon + path
    host, slash, path = rest.partition("/")
    return scheme.lower() + sep + host.lower() + slash + path


def _version(state):
    return state.get("version") or (state.get("revision") or "")[:12] or state.get("branch") or "?"


def pinned(path):
    """(source, version) of each package a Package.resolved pins (format versions 1-3)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") == 1:
            return sorted(
                (source(p["repositoryURL"]), _version(p["state"])) for p in data["object"]["pins"]
            )
        return sorted((source(p["location"]), _version(p["state"])) for p in data["pins"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise Unreadable(f"{path}: can't read its pins ({exc})") from exc


def reviewed(path):
    """(source, version) -> SPDX id from licenses.allow (blanks and # comments skipped)."""
    licenses = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError) as exc:
        raise Unreadable(f"{path}: {exc}") from exc
    for n, line in enumerate(lines, 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise Unreadable(f"{path}:{n}: expected `<location> <version> <SPDX id>`, got {line!r}")
        licenses[(source(parts[0]), parts[1])] = parts[2]
    return licenses


def main():
    root, allow = Path("."), Path("licenses.allow")
    locks = lockfiles(root)
    if not locks:
        print("license-audit: no Package.resolved, so no pinned dependencies to audit")
        return 0
    try:
        pins = sorted({pin for lock in locks for pin in pinned(lock)})
        licenses = reviewed(allow) if allow.exists() else {}
    except Unreadable as exc:
        print(f"license-audit: {exc}", file=sys.stderr)
        return 2
    problems = []
    for location, version in pins:
        spdx = licenses.get((location, version))
        if spdx is None:
            problems.append(f"{location} {version}: no reviewed license in licenses.allow")
        elif spdx not in ALLOWED:
            problems.append(f"{location} {version}: {spdx} is not on the allowlist")
    if problems:
        print("license-audit: FAIL (LEG-LICENSING-01)")
        for p in problems:
            print(f"  ✗ {p}")
        print(
            "  after checking each license, add `<location> <version> <SPDX id>` to "
            f"licenses.allow; allowed: {', '.join(sorted(ALLOWED))}; anything else needs a "
            "human decision"
        )
        return 1
    print(f"license-audit: clean ({len(pins)} pinned dependencies reviewed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
