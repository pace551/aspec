#!/usr/bin/env python3
"""What sec-sca.sh and sec-sast.sh need to know about a Swift project.

Usage (run from the project directory: Package.swift, *.xcodeproj or *.xcworkspace):

  swift-project.py sca     one line per finding, "<kind> <path>":
                             lock       a SwiftPM Package.resolved that pins packages
                             unpinned   remote packages with no lockfile pinning them
                             unaudited  a CocoaPods/Carthage lockfile (no scanner here)
  swift-project.py codeql  prints the workflow with a job that runs CodeQL on Swift and
                           sends its results somewhere (see results_go_somewhere); exit 3
                           if there is none

Exit 2 = a file couldn't be read or understood: the answer would be incomplete.

sca walks the project as it is on disk, which is what /verify-compliance checks: files not
yet committed and git submodules count, and so does a gitignored lockfile (that it is
committed is the scaffold's lockfile-check.py's job, in CI). Hidden directories, build/
at the top, and dependency and vendored trees (Pods, Carthage, DerivedData,
SourcePackages, node_modules) are skipped; symlinked directories aren't followed. Every
Package.resolved that pins packages is listed; one with no pins isn't (osv-scanner exits
128 on it). When remote packages are declared but no lockfile pins anything, each
declaring manifest is "unpinned". Which lockfile pins which project (a workspace's
lockfile covers the projects and local packages in it) isn't worked out: one pinned
lockfile anywhere satisfies it.

codeql parses the workflows rather than grepping them. GitHub runs only the repository
root's .github/workflows, so those are read (the project's own when it is the root or not
in a git repo). A job counts when an init step has swift among its languages (the matrix
expanded as GitHub does) and an analyze step follows it whose results go somewhere
(see results_go_somewhere), unless it is plainly switched
off: `if: false` on the job or either step, or a workflow with no trigger or only manual
ones (workflow_dispatch, repository_dispatch).
GitHub's other run conditions (a skipped job a job needs, a branch filter, whether a
reusable workflow has a caller) aren't modeled. CodeQL's default setup (enabled in the
repository settings, no workflow file) can't be seen from the checkout.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import sys
from pathlib import Path

import yaml

# a Swift string literal (multi-line, raw, or plain) or a comment: comments are dropped
# and strings blanked, so neither "//" in a URL nor text inside a string is read as code
SWIFT_TOKEN = re.compile(
    r'(#*)"""(?:\\.|[^\\])*?"""\1'  # multi-line, raw or not
    r'|(#+)"(?:[^"\n]|"(?!\2))*"\2'  # raw
    r'|"(?:\\.|[^"\\\n])*"'  # plain
    r"|//[^\n]*|/\*.*?\*/",
    re.DOTALL,
)
# .package(url: ...), .package(name: "x", url: ...) and registry .package(id: ...)
REMOTE_PACKAGE = re.compile(r"\.package\s*\([^)]*?\b(?:url|id)\s*:")
XCODE_REMOTE = re.compile(r"\bisa\s*=\s*XCRemoteSwiftPackageReference\s*;")
MATRIX_REF = re.compile(r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}")
NON_SWIFTPM_LOCKS = ("Podfile.lock", "Cartfile.resolved")
# build output, dependency checkouts and vendored trees: not the project's own manifests
SKIP_DIRS = {"Pods", "Carthage", "DerivedData", "SourcePackages", "node_modules"}
TOP_SKIP_DIRS = {"build"}  # xcodebuild -derivedDataPath build; deeper, it may be source
MANUAL_ONLY = {"workflow_dispatch", "repository_dispatch"}
KEPT = {"never", "false", "failure-only"}  # analyze's `upload`: anything else uploads
CONSTANT = re.compile(r"\$\{\{\s*(?:'([\w-]+)'|([\w-]+))\s*\}\}")  # ${{ false }}, ${{ 'never' }}
NAMES = {"Package.resolved", "project.pbxproj", *NON_SWIFTPM_LOCKS}
# Package.swift, and the version-specific Package@swift-6.0.swift SwiftPM prefers to it
MANIFEST = re.compile(r"Package(?:@swift-[\d.]+)?\.swift")


def wanted(name: str) -> bool:
    return name in NAMES or MANIFEST.fullmatch(name) is not None


class Incomplete(Exception):
    pass


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise Incomplete(f"can't read {path}: {e.strerror}") from e


def rel(path: Path) -> str:
    text = f"./{path.as_posix()}"
    if any(c in text for c in "\n\r\t"):
        raise Incomplete(f"control character in path {text!r}")
    return text


def pins(path: Path) -> int:
    try:
        data = json.loads(read(path))
        return len(data.get("pins") or (data.get("object") or {}).get("pins") or [])
    except (ValueError, AttributeError, TypeError) as e:
        raise Incomplete(f"{path} isn't a SwiftPM lockfile: {e}") from e


def code_of(manifest: Path) -> str:
    def blank(m: re.Match) -> str:
        return '""' if m[0].endswith(('"', "#")) else " "

    return SWIFT_TOKEN.sub(blank, read(manifest))


def project_files() -> list[Path]:
    def fail(e: OSError):
        raise Incomplete(f"can't list {e.filename}: {e.strerror}")

    found = []
    for top, dirs, files in os.walk(".", onerror=fail):
        skip = SKIP_DIRS | (TOP_SKIP_DIRS if top == "." else set())
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in skip)
        found += [Path(top, f) for f in sorted(files) if wanted(f)]
    return found


def sca() -> list[str]:
    pinned, remote, unaudited = [], [], []
    for path in project_files():
        if path.name == "Package.resolved" and pins(path):
            pinned.append(path)
        elif MANIFEST.fullmatch(path.name) and REMOTE_PACKAGE.search(code_of(path)):
            remote.append(path)
        elif path.name == "project.pbxproj" and path.parent.suffix == ".xcodeproj":
            if XCODE_REMOTE.search(read(path)):
                remote.append(path.parent)
        elif path.name in NON_SWIFTPM_LOCKS:
            unaudited.append(path)
    out = [f"lock {rel(p)}" for p in pinned]
    out += [] if pinned else [f"unpinned {rel(p)}" for p in remote]
    return out + [f"unaudited {rel(p)}" for p in unaudited]


def workflow_dir() -> Path:
    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            return parent / ".github" / "workflows"
    return here / ".github" / "workflows"


def is_false(cond) -> bool:
    text = re.sub(r"\s+", "", str(cond)).lower()
    return cond is False or text in ("false", "${{false}}")


def triggers(doc: dict) -> set[str]:
    on = doc.get("on", doc.get(True))  # YAML 1.1 reads a bare `on` key as true
    if isinstance(on, str):
        return {on}
    return {str(t) for t in on} if isinstance(on, (list, dict)) else set()


def matrix_values(job: dict, key: str) -> list[str]:
    """The values `key` takes across the job's matrix, expanded the way GitHub does: every
    combination of the axes, minus those an exclude entry matches; then each include is
    merged into every combination whose axis values it doesn't change (overwriting what an
    earlier include added), or becomes a combination of its own if it fits none."""
    matrix = (job.get("strategy") or {}).get("matrix")
    if not isinstance(matrix, dict):
        return []
    axes = {
        k: v if isinstance(v, list) else [v]
        for k, v in matrix.items()
        if k not in ("include", "exclude")
    }
    combos = (
        [dict(zip(axes, c, strict=True)) for c in itertools.product(*axes.values())] if axes else []
    )
    excludes = [e for e in matrix.get("exclude") or [] if isinstance(e, dict)]
    combos = [c for c in combos if not any(e.items() <= c.items() for e in excludes)]
    extra = []
    for inc in matrix.get("include") or []:
        if not isinstance(inc, dict):
            continue
        fits = [c for c in combos if all(c[k] == v for k, v in inc.items() if k in axes)]
        for c in fits:
            c.update(inc)
        if not fits:
            extra.append(inc)
    return [str(c[key]) for c in [*combos, *extra] if key in c]


def scalars(node) -> list[str]:
    if isinstance(node, dict):
        return [s for v in node.values() for s in scalars(v)]
    if isinstance(node, list):
        return [s for v in node for s in scalars(v)]
    return [] if node is None else [str(node)]


def action(step: dict) -> str:
    """The action a step uses, its owner/repo lowercased: GitHub matches those
    case-insensitively, but the path inside the repo is looked up as written."""
    owner, _, rest = str(step.get("uses", "")).partition("/")
    repo, slash, path = rest.partition("/")
    return f"{owner.lower()}/{repo.lower()}{slash}{path}" if rest else owner.lower()


def results_go_somewhere(steps: list[dict], analyze: int) -> bool:
    """False only when the analyze step at `analyze` keeps its results (upload: never,
    false or failure-only, as codeql-action reads it) and no later step sends them on or
    mentions them: no upload-sarif, and no part of the output path, nor sarif-output, in
    any value (run, env, with). Whether the results then block a merge (a failing step or
    code scanning's results check goes red, and red isn't merged) is SEC-SAST-05's
    attestation: no static reading of a workflow can tell."""
    options = steps[analyze].get("with") or {}
    upload = options.get("upload", "")
    # YAML reads an unquoted false as a boolean; GitHub hands the action the string "false"
    upload = str(upload).lower() if isinstance(upload, bool) else str(upload).strip()
    constant = CONSTANT.fullmatch(upload)
    if constant:  # a quoted string is passed as written; an unquoted keyword is a literal
        upload = constant[1] if constant[1] is not None else constant[2].lower()
    # codeql-action compares case-sensitively and uploads on any value it doesn't know
    if upload not in KEPT:
        return True
    later = steps[analyze + 1 :]
    if any(action(s).startswith("github/codeql-action/upload-sarif@") for s in later):
        return True
    parts = str(options.get("output", "../results")).split("/")
    needles = [r"\bsarif-output\b"] + [
        rf"(?<![\w.-]){re.escape(part.strip())}(?![\w-])"
        for part in parts
        if part.strip() not in ("", ".", "..")
    ]
    mention = re.compile("|".join(needles))
    return any(mention.search(s) for step in later for s in scalars(step))


def scans_swift(job: dict) -> bool:
    steps = [s for s in job.get("steps") or [] if not is_false(s.get("if"))]
    uses = [action(s) for s in steps]
    for i, used in enumerate(uses):
        if not used.startswith("github/codeql-action/init@"):
            continue
        languages = str((steps[i].get("with") or {}).get("languages", ""))
        languages = MATRIX_REF.sub(lambda m: ",".join(matrix_values(job, m[1])), languages)
        if "swift" not in (t.lower() for t in re.split(r"[\s,]+", languages)):
            continue
        if any(
            uses[j].startswith("github/codeql-action/analyze@") and results_go_somewhere(steps, j)
            for j in range(i + 1, len(steps))
        ):
            return True
    return False


def runs_codeql_on_swift(wf: Path) -> bool:
    doc = yaml.safe_load(read(wf))
    if not isinstance(doc, dict) or not triggers(doc) - MANUAL_ONLY:
        return False
    jobs = (doc.get("jobs") or {}).values()
    return any(not is_false(job.get("if")) and scans_swift(job) for job in jobs)


def codeql() -> str | None:
    wf_dir = workflow_dir()
    if not wf_dir.is_dir():
        return None
    try:
        files = sorted(p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml"))
    except OSError as e:
        raise Incomplete(f"can't list {wf_dir}: {e.strerror}") from e
    problems = []
    for wf in files:
        try:
            if runs_codeql_on_swift(wf):
                return str(wf)
        except Incomplete as e:
            problems.append(str(e))
        except (yaml.YAMLError, AttributeError, TypeError, RecursionError) as e:
            # a shape GitHub would reject too (a self-referencing anchor recurses); one
            # broken workflow mustn't hide another
            problems.append(f"can't understand {wf}: {type(e).__name__}: {e}")
    if problems:
        raise Incomplete("; ".join(problems))
    return None


def main(argv: list[str]) -> int:
    if argv not in (["sca"], ["codeql"]):
        print("usage: swift-project.py sca|codeql", file=sys.stderr)
        return 2
    try:
        if argv == ["sca"]:
            for line in sca():
                print(line)
            return 0
        found = codeql()
    except Incomplete as e:
        print(f"swift-project: {e}", file=sys.stderr)
        return 2
    if found is None:
        return 3
    print(found)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
