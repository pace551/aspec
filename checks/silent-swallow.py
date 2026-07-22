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
import re
import subprocess
import sys
from pathlib import Path

CATCHALL = {"Exception", "BaseException"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
EXCLUDED = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
EMPTY_CATCH = re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}")
MARKER = "swallow-ok:"


def project_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=True
        ).stdout
        return [root / p for p in out.split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [
            p
            for p in sorted(root.rglob("*"))
            if p.is_file() and not (set(p.relative_to(root).parts[:-1]) & EXCLUDED)
        ]


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
    scanned = 0
    for path in project_files(root):
        if not path.is_file():
            continue
        if path.suffix == ".py":
            scan_python(path, findings)
            scanned += 1
        elif path.suffix in JS_EXTS:
            scan_js(path, findings)
            scanned += 1

    if findings:
        print(f"silent-swallow: {len(findings)} silent exception swallow(s):")
        for f in findings:
            print(f"  ✗ {f}")
        print(
            "fix: handle it, translate it (`raise … from exc`), or let it propagate; "
            "a deliberate swallow needs `# swallow-ok: <reason>` on the except line"
        )
        return 1
    print(f"silent-swallow: clean ({scanned} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
