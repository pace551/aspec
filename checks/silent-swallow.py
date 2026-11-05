#!/usr/bin/env python3
"""silent-swallow.py — flag silently swallowed exceptions (backs ARC-ERRORS-01, layer G).

Findings:
  * Python: catch-all handlers (`except:`, `except Exception:`, `except BaseException:`,
    or tuples containing either) whose body is only `pass` / `...` / `continue`
  * JS/TS: empty `catch` blocks (`catch {}`, `catch (e) { }`)

Escape hatch: a `swallow-ok: <reason>` comment on the except/catch line (or the line
above) suppresses the finding — the written reason is what makes the swallow reviewable.

Read-only. Scans git-tracked files when run inside a repo, otherwise walks the tree with
standard excludes. Exit 0 = clean (including "nothing to scan"), 1 = findings, 2 = error.

Usage: python3 silent-swallow.py [--project DIR]
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import stat
import subprocess  # nosec B404 - argv-only subprocess use, audited below
import sys
from pathlib import Path

CATCHALL = {"Exception", "BaseException"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
ALWAYS_EXCLUDED = {".git", ".venv", "venv", "node_modules", "__pycache__"}
TOP_EXCLUDED = {"dist", "build"}
EMPTY_CATCH = re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}")
MARKER = "swallow-ok:"


def project_files(root: Path) -> list[Path]:
    """Tracked files; outside a git work tree, a walk with standard excludes. Raises
    OSError when git fails inside a repo, or the walk meets a directory it can't read
    (Path.rglob would skip it): either way the scan would be incomplete."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argv (git ls-files), no shell
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=False
        )
    except FileNotFoundError:
        proc = None  # no git at all
    if proc is not None:
        if proc.returncode == 0:  # paths are bytes: any name decodes (surrogateescape)
            return [root / os.fsdecode(p) for p in proc.stdout.split(b"\0") if p]
        err = proc.stderr.decode(errors="replace").strip()
        if "not a git repository" not in err:
            raise OSError(f"git ls-files failed: {err}")

    def fail(err: OSError) -> None:
        raise err

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=fail):
        # build/dist are output only at the top; deeper they may be first-party packages
        top = Path(dirpath) == root
        dirnames[:] = sorted(
            d for d in dirnames if d not in ALWAYS_EXCLUDED and not (top and d in TOP_EXCLUDED)
        )
        files.extend(Path(dirpath, f) for f in sorted(filenames))
    return files


def marked(lines: list[str], lineno: int) -> bool:
    """True when a swallow-ok marker sits on the flagged line or the line above."""
    for n in (lineno - 1, lineno - 2):
        if 0 <= n < len(lines) and MARKER in lines[n]:
            return True
    return False


def is_catchall(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    elts = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    for e in elts:
        name = e.id if isinstance(e, ast.Name) else (e.attr if isinstance(e, ast.Attribute) else "")
        if name in CATCHALL:
            return True
    return False


def body_swallows(handler: ast.ExceptHandler) -> bool:
    for stmt in handler.body:
        if isinstance(stmt, (ast.Pass, ast.Continue)):
            continue
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value is Ellipsis
        ):
            continue
        return False
    return True


def scan_python(path: Path, findings: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return  # not our job; the stack linter owns parse errors
    lines = text.splitlines()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ExceptHandler)
            and is_catchall(node)
            and body_swallows(node)
            and not marked(lines, node.lineno)
        ):
            findings.append(f"{path}:{node.lineno}: catch-all handler silently swallows")


def scan_js(path: Path, findings: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    for m in EMPTY_CATCH.finditer(text):
        lineno = text.count("\n", 0, m.start()) + 1
        if not marked(lines, lineno):
            findings.append(f"{path}:{lineno}: empty catch block silently swallows")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".", type=Path)
    args = ap.parse_args()
    root = args.project.resolve()
    if not root.is_dir():
        print(f"silent-swallow: not a directory: {root}", file=sys.stderr)
        return 2

    findings: list[str] = []
    unreadable: list[str] = []
    scanned = 0
    try:
        paths = project_files(root)
    except OSError as exc:
        print(f"silent-swallow: {exc} — scan incomplete", file=sys.stderr)
        return 2
    for path in paths:
        scan = scan_python if path.suffix == ".py" else scan_js if path.suffix in JS_EXTS else None
        if scan is None:
            continue
        # Path.is_file() is False for a file it can't stat, which skipped it silently
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                continue
            scan(path, findings)
        except FileNotFoundError:
            continue  # tracked but deleted in the work tree
        except OSError as exc:
            unreadable.append(f"{path}: {exc.strerror or exc}")
            continue
        scanned += 1

    if unreadable:
        print("silent-swallow: could not read — scan incomplete:", file=sys.stderr)
        for u in unreadable:
            print(f"  ✗ {u}", file=sys.stderr)
    if findings:
        print(f"silent-swallow: {len(findings)} silent exception swallow(s):")
        for f in findings:
            print(f"  ✗ {f}")
        print(
            "fix: handle it, translate it (`raise … from exc`), or let it propagate; "
            "a deliberate swallow needs `# swallow-ok: <reason>` on the except line"
        )
        return 1
    if unreadable:
        return 2
    print(f"silent-swallow: clean ({scanned} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
