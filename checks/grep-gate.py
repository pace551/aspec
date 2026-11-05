#!/usr/bin/env python3
"""grep-gate.py — the file-content checks behind standards' verification cmds.

Several standards check file contents with a one-liner: "no tracked .tf sets a public-read
ACL", "every Dockerfile sets a USER". Written with `grep -r`, `git grep` or `xargs grep -L`,
those one-liners passed when a file couldn't be read: grep's error went to /dev/null or to
a `! … | grep -q .` that only saw stdout, and `git grep` exits 1 ("no match") even after
"failed to stat". This script makes the same checks with one rule: a file it can't read
is an incomplete scan (exit 2), never a pass.

  forbid   fail when any selected file has a line matching any -e PATTERN
  require  fail when a selected file (that matches --if, when given) lacks any -e PATTERN

Files are what git tracks (plus untracked, not-ignored files with --untracked), so
.gitignore keeps node_modules/ and .venv/ out, and paths with spaces or non-ASCII stay
whole. --under DIR scans only below DIR (a missing DIR selects nothing; not combined
with PATHSPECs). Binary files (a NUL in the first 8 KiB), symlinks and directories
(submodules, nested repos) are skipped. Patterns are Python regexes,
matched per line (`^` and `$` anchor at line ends).

Usage:
  grep-gate.py forbid  -e PATTERN... [-i] [--untracked] [--under DIR]... [-- PATHSPEC...]
  grep-gate.py require -e PATTERN... [--if PATTERN] [-i] [--untracked] [--under DIR]...
                       [-- PATHSPEC...]
Exit 0 = pass, 1 = findings, 2 = usage error or incomplete scan. Read-only.
"""

from __future__ import annotations

import argparse
import re
import stat
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from pathlib import Path

BINARY_SNIFF = 8192


class Incomplete(Exception):
    pass


def selected_files(untracked: bool, under: list[str], pathspecs: list[str]) -> list[str]:
    # --under directories become the pathspecs, so git's walk stays inside them (an
    # unreadable directory elsewhere is none of this check's business); a missing one
    # simply selects nothing
    if under:
        pathspecs = [d.rstrip("/") for d in under]
    cmd = ["git", "ls-files", "-z", "--cached"]
    if untracked:
        cmd += ["--others", "--exclude-standard"]
    proc = subprocess.run(  # nosec B603 B607 - git ls-files, argv only, no shell
        [*cmd, "--", *pathspecs], capture_output=True, check=False
    )
    # git only warns ("could not open directory") about an unreadable untracked directory,
    # and exits 0: any stderr means files may be missing from the list.
    if proc.returncode != 0 or proc.stderr.strip():
        raise Incomplete(f"git ls-files: {proc.stderr.decode(errors='replace').strip()}")
    return sorted({f for f in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if f})


def read_text(path: str) -> str | None:
    """File text, or None for anything but a regular file (a symlink, a submodule or nested
    repo directory) or for a binary file. Raises Incomplete if unreadable."""
    p = Path(path)
    try:
        if not stat.S_ISREG(p.lstat().st_mode):
            return None
        data = p.read_bytes()
    except FileNotFoundError:
        return None  # tracked but deleted in the work tree: nothing to scan
    except OSError as exc:
        raise Incomplete(f"{path}: {exc.strerror or exc}") from exc
    if b"\0" in data[:BINARY_SNIFF]:
        return None
    return data.decode("utf-8", errors="replace")


def first_match(patterns: list[re.Pattern], text: str) -> tuple[int, str] | None:
    for n, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in patterns):
            return n, line
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["forbid", "require"])
    ap.add_argument("-e", dest="patterns", action="append", required=True)
    ap.add_argument("--if", dest="when")
    ap.add_argument("-i", dest="ignore_case", action="store_true")
    ap.add_argument("--untracked", action="store_true")
    ap.add_argument("--under", action="append", default=[])
    ap.add_argument("pathspecs", nargs="*")
    args = ap.parse_args()
    if args.when and args.mode != "require":
        ap.error("--if applies to require")
    if args.under and args.pathspecs:
        ap.error("--under and PATHSPECs don't combine")

    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        patterns = [re.compile(p, flags) for p in args.patterns]
        when = re.compile(args.when, flags) if args.when else None
    except re.error as exc:
        print(f"grep-gate: bad pattern: {exc}", file=sys.stderr)
        return 2

    findings: list[str] = []
    try:
        for path in selected_files(args.untracked, args.under, args.pathspecs):
            text = read_text(path)
            if text is None:
                continue
            if args.mode == "forbid":
                hit = first_match(patterns, text)
                if hit:
                    findings.append(f"{path}:{hit[0]}: {hit[1].strip()[:160]}")
            elif when is None or first_match([when], text):
                missing = [p.pattern for p in patterns if not first_match([p], text)]
                if missing:
                    findings.append(f"{path}: no line matches {' / '.join(missing)}")
    except Incomplete as exc:
        print(f"grep-gate: {exc} — scan incomplete", file=sys.stderr)
        return 2

    for f in findings:
        print(f, file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
