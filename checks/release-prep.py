#!/usr/bin/env python3
"""release-prep.py — release-time edits release-please doesn't make (release.yml).

ASPEC keeps a hand-written CHANGELOG.md, and its BSL Change Date moves with each
release. release-please (skip-changelog) handles the version and tag; this script
runs on the release PR branch to make the two edits that depend on the release:

  prepare  - LICENSE: `Change Date:` = release date + CHANGE_DATE_YEARS (Feb 29 ->
             Feb 28). CHANGELOG.md: moves the `## Unreleased` entries under a
             `## <version> — <date>` heading and leaves an empty `## Unreleased` on
             top. The version comes from .release-please-manifest.json, which
             release-please has already bumped on the release PR branch. Rerunning
             on a prepared branch only refreshes the date; if the version already
             has a section while Unreleased has entries (e.g. run by hand on main),
             it refuses rather than mix them into released history.
  notes    - prints the body of a version's CHANGELOG section (GitHub release notes).

Nothing is written unless both edits succeed; a missing `Change Date:` line or
`## Unreleased` heading exits 1.

Usage: python3 release-prep.py [--root DIR] prepare [--date YYYY-MM-DD]
       python3 release-prep.py [--root DIR] notes VERSION
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

CHANGE_DATE_YEARS = 3  # the offset the original Change Date used (2026-09-15 -> 2029-09-15)
UNRELEASED = "## Unreleased"
CHANGE_DATE = re.compile(r"^(Change Date:\s+)\d{4}-\d{2}-\d{2}$", re.MULTILINE)


def die(msg: str) -> None:
    print(f"release-prep: {msg}", file=sys.stderr)
    sys.exit(1)


def plus_years(day: dt.date, years: int) -> dt.date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # Feb 29 in a non-leap target year
        return day.replace(year=day.year + years, day=28)


def parse_sections(text: str) -> tuple[str, list[list[str]]]:
    """Split a changelog into its preamble and [heading, body] pairs at `## ` lines."""
    header: list[str] = []
    sections: list[list[str]] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections.append([line, ""])
        elif sections:
            sections[-1][1] += line + "\n"
        else:
            header.append(line)
    for section in sections:
        section[1] = section[1].strip()
    return "\n".join(header).rstrip("\n") + "\n", sections


def render(header: str, sections: list[list[str]]) -> str:
    rendered = [heading + "\n" + (f"\n{body}\n" if body else "") for heading, body in sections]
    return header + "\n" + "\n".join(rendered)


def version_heading(version: str) -> re.Pattern:
    return re.compile(rf"^## {re.escape(version)}( — .*)?$")


def prepare(root: Path, day: dt.date) -> None:
    version = json.loads((root / ".release-please-manifest.json").read_text())["."]

    license_text = (root / "LICENSE").read_text()
    new_date = plus_years(day, CHANGE_DATE_YEARS).isoformat()
    if not CHANGE_DATE.search(license_text):
        die("LICENSE has no 'Change Date:' line to update")
    license_text = CHANGE_DATE.sub(rf"\g<1>{new_date}", license_text, count=1)

    header, sections = parse_sections((root / "CHANGELOG.md").read_text())
    headings = [heading for heading, _ in sections]
    if UNRELEASED not in headings:
        die(f"CHANGELOG.md has no '{UNRELEASED}' heading")
    at = headings.index(UNRELEASED)
    pending = sections[at][1]
    match = version_heading(version)
    existing = [s for s in sections if match.match(s[0])]
    if existing and pending:
        die(f"CHANGELOG.md already has a {version} section and Unreleased has entries; "
            "refusing to fold them into it (run on the release PR branch, where "
            "release-please has bumped the version)")
    if existing:  # rerun on an already-prepared branch: refresh the date only
        existing[0][0] = f"## {version} — {day.isoformat()}"
    else:
        sections[at][1] = ""
        sections.insert(at + 1, [f"## {version} — {day.isoformat()}", pending])

    (root / "LICENSE").write_text(license_text)
    (root / "CHANGELOG.md").write_text(render(header, sections))
    print(f"release-prep: {version} — Change Date {new_date}, CHANGELOG section dated {day}")


def notes(root: Path, version: str) -> None:
    _, sections = parse_sections((root / "CHANGELOG.md").read_text())
    match = version_heading(version)
    for heading, body in sections:
        if match.match(heading):
            print(body)
            return
    die(f"CHANGELOG.md has no section for {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--date", type=dt.date.fromisoformat,
                      default=dt.datetime.now(dt.UTC).date())
    note = commands.add_parser("notes")
    note.add_argument("version")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root, args.date)
    else:
        notes(args.root, args.version)


if __name__ == "__main__":
    main()
