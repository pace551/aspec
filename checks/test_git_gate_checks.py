#!/usr/bin/env python3
"""Unit tests for the git-hook and linear-history verification cmds.

DEV-BOOTSTRAP-06 / DEV-CI-02 must pass on a repo whose hooks came from the official
installer (templates/scaffolds/_common/install-git-hooks.sh sets core.hooksPath), and
DEV-GIT-03 must judge only recent main history, not a merge commit from long ago.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "templates" / "scaffolds" / "_common" / "install-git-hooks.sh"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]


def verification_cmd(standard: str, rule: str) -> str:
    text = (ROOT / "standards" / "process" / f"{standard}.md").read_text()
    front = yaml.safe_load(re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL).group(1))
    return next(str(v["cmd"]) for v in front["verification"] if rule in v["rules"])


HOOK_CMDS = {
    rule: verification_cmd(std, rule)
    for std, rule in [("dev-bootstrap", "DEV-BOOTSTRAP-06"), ("dev-ci", "DEV-CI-02")]
}
LINEAR_CMD = verification_cmd("dev-git", "DEV-GIT-03")


def run(cmd: str, cwd: Path) -> int:
    return subprocess.run(
        ["bash", "-c", cmd],
        cwd=cwd,
        capture_output=True,
        env={**os.environ, "GOVERNANCE_DIR": str(ROOT)},
        check=False,
    ).returncode


def git(repo: Path, *args: str) -> None:
    subprocess.run([*GIT, *args], cwd=repo, capture_output=True, check=True)


def commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "commit", "-qm", f"chore: {name}")


class HookCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q")

    def tearDown(self):
        self._tmp.cleanup()

    def test_official_installer_passes(self):
        subprocess.run(
            ["bash", str(INSTALLER)],
            cwd=self.repo,
            capture_output=True,
            env={**os.environ, "GOVERNANCE_DIR": str(ROOT)},
            check=True,
        )
        for rule, cmd in HOOK_CMDS.items():
            self.assertEqual(run(cmd, self.repo), 0, rule)

    def test_hooks_in_default_dir_pass(self):
        for name in ("pre-commit", "pre-push"):
            hook = self.repo / ".git" / "hooks" / name
            hook.write_text("#!/bin/sh\n")
            hook.chmod(0o755)
        for rule, cmd in HOOK_CMDS.items():
            self.assertEqual(run(cmd, self.repo), 0, rule)

    def test_no_hooks_fails(self):
        for rule, cmd in HOOK_CMDS.items():
            self.assertNotEqual(run(cmd, self.repo), 0, rule)

    def test_hooks_path_set_but_hooks_missing_fails(self):
        git(self.repo, "config", "core.hooksPath", ".githooks")
        for rule, cmd in HOOK_CMDS.items():
            self.assertNotEqual(run(cmd, self.repo), 0, rule)


class LinearHistoryCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q")
        commit(self.repo, "base")

    def tearDown(self):
        self._tmp.cleanup()

    def merge_side_branch(self) -> None:
        git(self.repo, "switch", "-qc", "side")
        commit(self.repo, "side")
        git(self.repo, "switch", "-q", "main")
        commit(self.repo, "main-only")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'side'", "side")

    def test_linear_history_passes(self):
        commit(self.repo, "second")
        self.assertEqual(run(LINEAR_CMD, self.repo), 0)

    def test_recent_merge_fails(self):
        self.merge_side_branch()
        commit(self.repo, "after")
        self.assertNotEqual(run(LINEAR_CMD, self.repo), 0)

    def test_merge_older_than_the_window_passes(self):
        self.merge_side_branch()
        for i in range(20):
            commit(self.repo, f"linear-{i}")
        self.assertEqual(run(LINEAR_CMD, self.repo), 0)

    def test_no_main_branch_passes(self):
        git(self.repo, "branch", "-m", "main", "trunk")
        self.assertEqual(run(LINEAR_CMD, self.repo), 0)


if __name__ == "__main__":
    unittest.main()
