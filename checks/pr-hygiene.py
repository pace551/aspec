#!/usr/bin/env python3
"""Check this repo's own PR rules (CLAUDE.md) on the commits a branch adds.

- A PR is exactly one squashed commit since its merge base with the target branch.
- Its subject is a conventional commit (Constitution C4), or git's `Revert "…"` /
  `Reapply "…"` around one.
- A `feat`, `fix` or breaking change (`!` in the subject or a `BREAKING CHANGE:` footer)
  adds words to CHANGELOG.md's `## Unreleased` section. Rewrapping, reordering, deleting
  and subheadings don't count; prose or bullets of any style do. Reverting one acts on
  the reverted commit's entry (found by `git blame`): drops it while unreleased, records
  the revert once a
  release (`chore(main): release …`) has shipped it.

PRs opened by bots (release-please, Dependabot) are skipped by the CI job, which knows the
PR's author; this script itself exempts nothing.

Usage: pr-hygiene.py [--base REF] [--head REF]   (defaults: origin/main, HEAD)
Exit 0 = clean, 1 = a rule is broken, 2 = git couldn't resolve the refs.
Run by the CI pr-hygiene job and by this repo's scripts/pre-push.sh.
"""

from __future__ import annotations

import argparse
import re
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from collections import Counter

CONVENTIONAL_RE = re.compile(
    r"^(?P<type>build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    r"(?:\([^()\s]+\))?(?P<breaking>!)?: \S"
)
# git's own subjects for undoing and redoing a commit, which DEV-GIT-01 accepts:
# `Revert "<subject>"`, and for a revert of a revert `Reapply "<subject>"` (git 2.43+) or
# `Revert "Revert "<subject>""` (older git)
GIT_REVERT_RE = re.compile(r'^(Revert|Reapply) "(.+)"$')
BREAKING_FOOTER_RE = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
REVERTS_RE = re.compile(r"^This reverts commit ([0-9a-f]{7,64})", re.MULTILINE)
NEEDS_CHANGELOG = {"feat", "fix"}
UNRELEASED = "## Unreleased"
LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)])$")
LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:\s|$)")  # CommonMark ATX heading
FIELD, RECORD = "\x1f", "\x1e"


class GitError(Exception):
    pass


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, check=False)  # nosec B603 B607
    if r.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def unreleased_words(rev: str) -> Counter[str]:
    """The words of CHANGELOG.md's `## Unreleased` section at rev, counted, without its
    subheadings and list markers: the hand-written text, however wrapped, bulleted or
    ordered."""
    try:
        lines = git("show", f"{rev}:CHANGELOG.md").splitlines()
        start = lines.index(UNRELEASED) + 1
    except (GitError, ValueError):
        return Counter()
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return Counter(
        word
        for line in lines[start:end]
        if not HEADING_RE.match(line)
        for word in line.split()
        if not LIST_MARKER_RE.match(word)
    )


def revert_chain(body: str, limit: int = 20) -> list[tuple[str, str]]:
    """(sha, body) of body's own commit ("" for its sha) and of the commits it reverts,
    back through revert-of-revert chains to the original change: a breaking footer and a
    CHANGELOG entry live on the original, not on its reverts."""
    chain, seen = [("", body)], set()
    while (sha := REVERTS_RE.search(chain[-1][1])) and sha[1] not in seen and len(seen) < limit:
        seen.add(sha[1])
        try:
            chain.append((sha[1], git("log", "-1", "--format=%b", sha[1])))
        except GitError:
            break  # not in this clone: judge by what we have
    return chain


RELEASE_RE = re.compile(r"^chore\(main\): release ", re.MULTILINE)


def section_bounds(lines: list[str]) -> tuple[int, int]:
    """[start, end) of the `## Unreleased` body in CHANGELOG.md's lines ((0, 0) if none)."""
    try:
        start = lines.index(UNRELEASED) + 1
    except ValueError:
        return 0, 0
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end


def entry_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """[start, end) line spans of the entries in lines: a list item at column 0 or a
    paragraph, with its indented continuation lines. Blank lines and headings separate."""
    spans: list[tuple[int, int]] = []
    start = None
    for n, line in enumerate(lines + [""]):
        new_item = bool(LIST_ITEM_RE.match(line))
        if not line.strip() or HEADING_RE.match(line) or new_item:
            if start is not None:
                spans.append((start, n))
            start = n if new_item else None
        elif start is None:
            start = n
    return spans


def block_text(lines: list[str]) -> str:
    """An entry's words, whitespace-normalized and without its list marker: a rewrap or
    a new bullet style is the same entry."""
    words = " ".join(lines).split()
    return " ".join(words[1:] if words and LIST_MARKER_RE.match(words[0]) else words)


def unreleased_entries(rev: str, by: str = "") -> Counter[str]:
    """CHANGELOG.md's `## Unreleased` entries at rev (counted). With by, only the entries
    holding a line `git blame` attributes to that commit: its entry, if not reworded."""
    try:
        if by:
            by = git("rev-parse", by).strip()
            porcelain = git("blame", "--porcelain", rev, "--", "CHANGELOG.md").splitlines()
        else:
            porcelain = ["\t" + line for line in git("show", f"{rev}:CHANGELOG.md").splitlines()]
    except GitError:
        return Counter()
    blamed: list[tuple[str, str]] = []  # (commit, line) in file order
    commit = ""
    for line in porcelain:
        if line.startswith("\t"):
            blamed.append((commit, line[1:]))
        elif re.match(r"^[0-9a-f]{40} \d+ \d+", line):
            commit = line.split(" ", 1)[0]
    start, end = section_bounds([text for _, text in blamed])
    section = blamed[start:end]
    texts = [text for _, text in section]
    return Counter(
        block_text(texts[a:b])
        for a, b in entry_blocks(texts)
        if not by or any(c == by for c, _ in section[a:b])
    )


def section_lines(rev: str, by: str = "") -> Counter[str]:
    """The non-blank `## Unreleased` lines at rev, stripped and counted; with by, only those
    `git blame` attributes to that commit. Counted, because identical lines are
    interchangeable: git itself can't say which copy a commit added."""
    try:
        if by:
            by = git("rev-parse", by).strip()
            porcelain = git("blame", "--porcelain", rev, "--", "CHANGELOG.md").splitlines()
        else:
            porcelain = ["\t" + line for line in git("show", f"{rev}:CHANGELOG.md").splitlines()]
    except GitError:
        return Counter()
    lines: list[tuple[str, str]] = []
    commit = ""
    for line in porcelain:
        if line.startswith("\t"):
            lines.append((commit, line[1:]))
        elif re.match(r"^[0-9a-f]{40} \d+ \d+", line):
            commit = line.split(" ", 1)[0]
    start, end = section_bounds([text for _, text in lines])
    return Counter(
        text.strip()
        for c, text in lines[start:end]
        # a subheading can be shared by later entries: it's structure, not the entry
        if text.strip() and not HEADING_RE.match(text) and (not by or c == by)
    )


def released_since(sha: str, upto: str) -> bool:
    """Whether a release-please release commit landed after sha (up to upto): then sha's
    change has shipped, whatever its CHANGELOG entry says now."""
    return bool(RELEASE_RE.search(git("log", "--format=%s", f"{sha}..{upto}")))


def check(base: str, head: str) -> list[str]:
    merge_base = git("merge-base", base, head).strip()
    log = git("log", "--topo-order", f"--format=%s{FIELD}%b{RECORD}", f"{merge_base}..{head}")
    commits = [r.lstrip("\n").split(FIELD, 1) for r in log.split(RECORD) if r.strip()]
    if not commits:
        return []

    problems = []
    if len(commits) != 1:
        problems.append(
            f"{len(commits)} commits since the merge base with {base}; a PR is one squashed "
            f"commit (git reset --soft {merge_base[:12]} && git commit)"
        )
    subject, body = commits[0]  # --topo-order lists the tip first, whatever the dates
    inner, reverted = subject, False
    while g := GIT_REVERT_RE.match(inner):
        inner, reverted = g[2], reverted != (g[1] == "Revert")
    m = CONVENTIONAL_RE.match(inner)
    if not m:
        problems.append(
            f"subject isn't a conventional commit (C4): {subject!r}; use "
            "`type(scope)!: summary` with type one of "
            "build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test"
        )
        return problems
    chain = revert_chain(body)
    breaking = bool(m["breaking"] or any(BREAKING_FOOTER_RE.search(b) for _, b in chain))
    if m["type"] not in NEEDS_CHANGELOG and not breaking:
        return problems
    kind = "breaking" if breaking else m["type"]
    old, new = unreleased_words(merge_base), unreleased_words(head)
    if reverted and not BREAKING_FOOTER_RE.search(body):  # a revert's own footer: new change
        # Whether the reverted commit has shipped decides it: a release since then means
        # the revert needs an entry of its own; none means it removes the change's entry
        # (whatever its wording by now). Not in this clone: any change to the section.
        target = chain[1][0] if len(chain) > 1 else ""
        if target and released_since(target, merge_base):
            if not new - old:
                problems.append(
                    f"reverting a released {kind} change must add an entry under "
                    f"`{UNRELEASED}` in CHANGELOG.md saying it was reverted"
                )
        elif target:
            # its entry, found by blame; reworded since (blame points elsewhere), any
            # removed entry text has to do
            # Every line of its entry must go (a partial deletion leaves it described),
            # and the entry mustn't come back rewrapped (compared whole).
            entry = unreleased_entries(merge_base, by=target)
            left = section_lines(merge_base, by=target) - (
                section_lines(merge_base) - section_lines(head)
            )
            removed = unreleased_entries(merge_base) - unreleased_entries(head)
            kept = entry - removed
            if left or kept or (not entry and not old - new):
                problems.append(
                    f"reverting an unreleased {kind} change must remove its entry from "
                    f"`{UNRELEASED}` in CHANGELOG.md"
                    + (f" (still there: {next(iter(kept))!r})" if kept else "")
                )
        elif old == new:
            problems.append(
                f"reverting a {kind} change must update `{UNRELEASED}` in CHANGELOG.md: "
                "remove its entry if it's unreleased, or add one saying it was reverted"
            )
    elif not new - old:
        problems.append(
            f"a {kind} change needs new text under `{UNRELEASED}` in CHANGELOG.md (CLAUDE.md)"
        )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args()
    try:
        problems = check(args.base, args.head)
    except GitError as exc:
        print(f"pr-hygiene: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("pr-hygiene: FAIL\n" + "\n".join(f"  ✗ {p}" for p in problems))
        return 1
    print(f"pr-hygiene: clean ({args.base}..{args.head})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
