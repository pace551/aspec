"""Hostile project trees for testing ASPEC's checks (test helper, imported by tests only).

Devin's reviews of #16-#38 kept finding checks that broke on ordinary-but-awkward
filesystems: a path with a space split by `xargs`, a `find` error hidden by process
substitution so an unreadable directory passed, an unreadable excluded `node_modules/`
aborting a scan. A Tree builds a throwaway project with those features on demand:

- files at any relative path (spaces and non-ASCII welcome), tracked in git or not
- `locked(rel)`: a directory the scan can't read (chmod 000), restored on exit
- `symlink_loop(rel)`: a directory symlink pointing back at an ancestor
- `nested_repo(rel)`: a git repo inside the project (a gitlink once committed)

Builds its own git repo with no inherited GIT_* variables (see checks/conftest.py).
"""

from __future__ import annotations

import contextlib
import os
import subprocess  # nosec B404 - fixed git argv, no shell (test helper)
import tempfile
from collections.abc import Iterator
from pathlib import Path

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
# A path segment no check should trip over: a space, combining-free non-ASCII, and a dash.
HOSTILE_DIR = "my dir/ünïcødé-x"
# Directories every walking check must skip (and so must survive being unreadable).
EXCLUDED_DIRS = ("node_modules", ".venv")
GITIGNORE = "".join(f"{d}/\n" for d in EXCLUDED_DIRS)


def clean_env(**extra: str) -> dict[str, str]:
    """os.environ without GIT_* variables (a hook's GIT_DIR would redirect the throwaway
    repo's git commands to the real one), plus overrides."""
    return {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")}, **extra}


def can_lock() -> bool:
    """chmod 000 stops nobody when running as root."""
    return os.geteuid() != 0


class Tree:
    def __init__(self, root: Path):
        self.root = root

    def write(self, files: dict[str, str]) -> Tree:
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return self

    def git(self, *args: str) -> str:
        return subprocess.run(  # nosec B603 B607 - git with fixed args, no shell
            [*GIT, *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=clean_env(),
            check=True,
        ).stdout

    def commit(self, message: str = "chore: fixture") -> Tree:
        """git init (once), stage everything not ignored, and commit."""
        if not (self.root / ".git").exists():
            self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self

    @contextlib.contextmanager
    def locked(self, rel: str) -> Iterator[Path]:
        path = self.root / rel
        mode = path.stat().st_mode
        path.chmod(0)
        try:
            yield path
        finally:
            path.chmod(mode)

    def nested_repo(self, rel: str) -> Tree:
        """A git repo of its own at rel: a submodule-like gitlink once the outer repo
        commits it, an untracked `rel/` entry before."""
        path = self.root / rel
        path.mkdir(parents=True, exist_ok=True)
        Tree(path).write({"README": "nested\n"}).commit()
        return self

    def symlink_loop(self, rel: str) -> Tree:
        """rel/loop -> rel's parent tree: endless for anything that follows dir symlinks."""
        path = self.root / rel
        path.mkdir(parents=True, exist_ok=True)
        (path / "loop").symlink_to(os.path.relpath(self.root, path), target_is_directory=True)
        return self


@contextlib.contextmanager
def tree() -> Iterator[Tree]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp, "proj")
        root.mkdir()
        t = Tree(root)
        try:
            yield t
        finally:
            # a test that failed inside locked() must not leave an undeletable dir behind
            for dirpath, dirnames, _ in os.walk(root):
                for d in dirnames:
                    p = Path(dirpath, d)
                    if not p.is_symlink():
                        p.chmod(0o755)
