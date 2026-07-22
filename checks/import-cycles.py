#!/usr/bin/env python3
"""import-cycles.py — first-party import graph must be acyclic (ARC-MODULARITY-01, layer G).

Parses every Python module under src/ (fallback: top-level packages containing an
__init__.py), resolves absolute and relative first-party imports — ignoring
`if TYPE_CHECKING:` blocks, which cannot cause runtime cycles — and reports strongly
connected components of size > 1 (plus self-imports).

Exit 0 = acyclic, or no Python package present (fresh scaffold / non-Python project);
1 = at least one import cycle; 2 = error. Read-only.

Usage: python3 import-cycles.py [--project DIR] [--src DIR]
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

EXCLUDED = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}


def collect_files(root: Path, src_override: Path | None) -> list[tuple[Path, Path]]:
    """(base, file) pairs; a file's module name is its path relative to base."""
    if src_override is not None:
        base = src_override if src_override.is_absolute() else root / src_override
        return [(base, f) for f in sorted(base.rglob("*.py"))] if base.is_dir() else []
    src = root / "src"
    if src.is_dir():
        return [(src, f) for f in sorted(src.rglob("*.py"))]
    pairs: list[tuple[Path, Path]] = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and d.name not in EXCLUDED and (d / "__init__.py").exists():
            pairs.extend((root, f) for f in sorted(d.rglob("*.py")))
    return pairs


def module_name(base: Path, f: Path) -> str:
    parts = list(f.relative_to(base).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


class Imports(ast.NodeVisitor):
    """Collect import nodes, skipping `if TYPE_CHECKING:` bodies."""

    def __init__(self) -> None:
        self.nodes: list[ast.Import | ast.ImportFrom] = []

    def visit_If(self, node: ast.If) -> None:
        if "TYPE_CHECKING" not in ast.dump(node.test):
            for stmt in node.body:
                self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Import(self, node: ast.Import) -> None:
        self.nodes.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.nodes.append(node)


def resolve(name: str, known: set[str]) -> str | None:
    """Longest known prefix of a dotted name (module or package), else None."""
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in known:
            return cand
    return None


def build_graph(pairs: list[tuple[Path, Path]]) -> dict[str, set[str]]:
    mods: dict[str, tuple[Path, Path]] = {}
    is_pkg: dict[str, bool] = {}
    for base, f in pairs:
        name = module_name(base, f)
        if name:
            mods[name] = (base, f)
            is_pkg[name] = f.name == "__init__.py"
    known = set(mods)
    graph: dict[str, set[str]] = {m: set() for m in known}

    for name, (_base, f) in mods.items():
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        collector = Imports()
        collector.visit(tree)
        for node in collector.nodes:
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            else:
                if node.level:  # relative import
                    pkg_parts = name.split(".") if is_pkg[name] else name.split(".")[:-1]
                    up = node.level - 1
                    if up > len(pkg_parts):
                        continue
                    prefix = pkg_parts[: len(pkg_parts) - up]
                    extra = node.module.split(".") if node.module else []
                    base_mod = ".".join(prefix + extra)
                else:
                    base_mod = node.module or ""
                for a in node.names:
                    targets.append(f"{base_mod}.{a.name}" if base_mod else a.name)
                if base_mod:
                    targets.append(base_mod)
            for t in targets:
                r = resolve(t, known)
                if r and r != name:
                    graph[name].add(r)
    return graph


def tarjan(graph: dict[str, set[str]]) -> list[list[str]]:
    sys.setrecursionlimit(max(10_000, 10 * len(graph) + 100))
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[list[str]] = []
    counter = [0]

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph[v]:
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in sorted(graph):
        if v not in index:
            strong(v)
    return sccs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".", type=Path)
    ap.add_argument("--src", default=None, type=Path, help="module root (default: src/)")
    args = ap.parse_args()
    root = args.project.resolve()
    if not root.is_dir():
        print(f"import-cycles: not a directory: {root}", file=sys.stderr)
        return 2

    pairs = collect_files(root, args.src)
    if not pairs:
        print("import-cycles: no Python package found (src/ or top-level) — nothing to check")
        return 0

    graph = build_graph(pairs)
    cycles = [
        sorted(c) for c in tarjan(graph) if len(c) > 1 or (c and c[0] in graph[c[0]])
    ]
    if cycles:
        print(f"import-cycles: {len(cycles)} import cycle(s) found:")
        for c in cycles:
            print(f"  ✗ {' → '.join(c)} → {c[0]}")
        print("fix: invert the dependency (move the shared piece down, or inject it); "
              "don't hide the cycle behind function-local imports")
        return 1
    print(f"import-cycles: clean ({len(graph)} modules, acyclic)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
