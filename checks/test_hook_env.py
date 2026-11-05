#!/usr/bin/env python3
"""Tests that a git hook's environment can't redirect the tests' throwaway repos.

Git exports GIT_DIR to a hook run from a linked worktree (and leaves GIT_WORK_TREE unset,
so git takes the current directory as the work tree). The pre-push hook runs this test
suite; tests that `git init` / `git add` / `git commit` in a temp dir then acted on the
real repository instead, staging every tracked file as deleted. checks/conftest.py drops
GIT_* variables for the whole test session, and the scaffold pre-push hook runs
scripts/test.sh without them.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "templates" / "scaffolds" / "_common" / "githooks" / "pre-push"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
# A few tests from each file that builds throwaway repos with git.
GIT_TESTS = [
    "checks/test_pr_hygiene.py::PrHygieneTests::test_two_commits_fail",
    "checks/test_git_gate_checks.py::LinearHistoryCheckTests::test_linear_history_passes",
    "checks/test_xargs_null.py::VerificationCmdTests::test_inf_containers_user",
]


def git(*args: str, cwd: Path) -> str:
    return subprocess.run([*GIT, *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def snapshot(wt: Path) -> tuple[str, str, str]:
    return (
        git("status", "--porcelain", cwd=wt),
        git("rev-parse", "HEAD", cwd=wt),
        git("branch", "--list", cwd=wt),
    )


class HookGitDirTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.host, self.wt = tmp / "host", tmp / "wt"
        self.host.mkdir()
        git("init", "-q", cwd=self.host)
        (self.host / "tracked.txt").write_text("x\n")
        git("add", "tracked.txt", cwd=self.host)
        git("commit", "-qm", "chore: base", cwd=self.host)
        git("worktree", "add", "-q", "-b", "wt", str(self.wt), cwd=self.host)
        # What git exports to a hook run from a linked worktree: GIT_DIR only.
        self.hook_env = {
            **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "GIT_DIR": git("rev-parse", "--absolute-git-dir", cwd=self.wt).strip(),
        }

    def tearDown(self):
        self._tmp.cleanup()

    def test_tests_leave_the_pushing_repo_alone(self):
        before = snapshot(self.wt)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *GIT_TESTS],
            cwd=ROOT,
            env=self.hook_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(snapshot(self.wt), before)

    def test_scaffold_hook_runs_tests_without_repo_variables(self):
        scripts = self.wt / "scripts"
        scripts.mkdir()
        log = Path(self._tmp.name, "env.log")
        test_sh = scripts / "test.sh"
        test_sh.write_text(f'#!/bin/sh\nenv | grep "^GIT_" | cut -d= -f1 > "{log}"\nexit 0\n')
        test_sh.chmod(0o755)
        gitdir = self.hook_env["GIT_DIR"]
        # what a hook can see: git's own exports plus repo variables from the user's shell
        env = {
            **self.hook_env,
            "GIT_PREFIX": "",
            "GIT_EXEC_PATH": git("--exec-path", cwd=self.wt).strip(),
            "GIT_WORK_TREE": str(self.wt),
            "GIT_INDEX_FILE": f"{gitdir}/index",
            "GIT_COMMON_DIR": git("rev-parse", "--git-common-dir", cwd=self.wt).strip(),
            "GIT_CONFIG_PARAMETERS": "'core.hookspath'='.githooks'",
        }
        proc = subprocess.run(
            ["bash", str(HOOK), "origin", "https://example.invalid/r.git"],
            cwd=self.wt,
            env=env,
            input="",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        local = set(git("rev-parse", "--local-env-vars", cwd=self.wt).split())
        self.assertEqual(set(log.read_text().split()) & local, set())


if __name__ == "__main__":
    unittest.main()
