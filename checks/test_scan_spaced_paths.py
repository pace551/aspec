#!/usr/bin/env python3
"""Tests that the IaC/container scanners keep paths with spaces whole.

inf-container-scan.sh and inf-tf-scan.sh collected files into a string and looped
`for f in $LIST`, which word-splits: `svc a/Dockerfile` reached the linters as `./svc`
and `a/Dockerfile`, so a spaced path was never checked and a compliant one could fail.
Both now read NUL-separated `find -print0` output into bash arrays (bash 3.2-safe: no
mapfile). Stub linters on PATH record the exact arguments they receive.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTAINER_SCAN = ROOT / "checks" / "inf-container-scan.sh"
TF_SCAN = ROOT / "checks" / "inf-tf-scan.sh"
BASE_PATH = "/usr/bin:/bin"  # no hadolint/trivy/tofu/tflint/checkov here


def stub(bindir: Path, name: str, log: Path) -> None:
    """A fake tool that logs its cwd and each argument (one per line) and succeeds."""
    script = bindir / name
    script.write_text(
        "#!/bin/sh\n"
        f'{{ echo "{name} cwd=$PWD"; for a in "$@"; do echo "  arg=$a"; done; }} >> "{log}"\n'
        "exit 0\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


def run(script: Path, project: Path, path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/bin/bash", str(script), "--project", str(project)],
        env={**os.environ, "PATH": path},
        capture_output=True,
        text=True,
        check=False,
    )


class ContainerScanTests(unittest.TestCase):
    def project(self, tmp: str, dockerfile: str) -> Path:
        proj = Path(tmp, "proj")
        (proj / "svc a").mkdir(parents=True)
        (proj / "svc a" / "Dockerfile").write_text(dockerfile)
        (proj / ".dockerignore").write_text(".git\n")
        return proj

    def test_linters_receive_the_whole_spaced_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self.project(tmp, "FROM alpine:3.20\nUSER app\n")
            bindir, log = Path(tmp, "bin"), Path(tmp, "calls.log")
            bindir.mkdir()
            for tool in ("hadolint", "trivy"):
                stub(bindir, tool, log)
            proc = run(CONTAINER_SCAN, proj, f"{bindir}:{BASE_PATH}")
            calls = log.read_text() if log.exists() else ""
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(calls.count("  arg=./svc a/Dockerfile\n"), 2, calls)
        self.assertNotIn("arg=./svc\n", calls)

    def test_fallback_passes_a_compliant_spaced_dockerfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self.project(tmp, "FROM alpine:3.20\nUSER app\n")
            proc = run(CONTAINER_SCAN, proj, BASE_PATH)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_fallback_fails_a_noncompliant_spaced_dockerfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self.project(tmp, "FROM alpine\n")
            proc = run(CONTAINER_SCAN, proj, BASE_PATH)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("./svc a/Dockerfile: no USER instruction", proc.stderr)
        self.assertIn("./svc a/Dockerfile: base image 'alpine' is unpinned", proc.stderr)


class TfScanTests(unittest.TestCase):
    def test_every_tool_runs_in_the_whole_spaced_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp, "proj")
            (proj / "infra" / "my mod").mkdir(parents=True)
            (proj / "infra" / "my mod" / "main.tf").write_text('variable "x" {}\n')
            (proj / "main.tf").write_text('variable "y" {}\n')
            bindir, log = Path(tmp, "bin"), Path(tmp, "calls.log")
            bindir.mkdir()
            for tool in ("tofu", "tflint", "checkov"):
                stub(bindir, tool, log)
            proc = run(TF_SCAN, proj, f"{bindir}:{BASE_PATH}")
            calls = log.read_text() if log.exists() else ""
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # tofu fmt -check (working tree) + init + validate (temp copy), per directory
        self.assertEqual(calls.count("/infra/my mod\n  arg=fmt"), 1, calls)
        self.assertEqual(calls.count("/infra/my mod\n  arg=init"), 1, calls)
        self.assertEqual(calls.count("/infra/my mod\n  arg=validate"), 1, calls)
        self.assertIn("  arg=--chdir\n  arg=./infra/my mod\n", calls)
        self.assertIn("  arg=-d\n  arg=./infra/my mod\n", calls)
        self.assertIn("  arg=--chdir\n  arg=.\n", calls)
        self.assertNotIn("arg=./infra/my\n", calls)


class UnreadableDirTests(unittest.TestCase):
    """A directory find can't enter is an incomplete scan: exit 2, never a silent pass."""

    def setUp(self):
        if os.geteuid() == 0:
            self.skipTest("root can read any directory")

    def scan(self, script: Path, rel: str, content: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp, "proj")
            locked = proj / rel
            locked.mkdir(parents=True)
            (locked / ("Dockerfile" if script == CONTAINER_SCAN else "main.tf")).write_text(content)
            locked.chmod(0)
            try:
                return run(script, proj, BASE_PATH)
            finally:
                locked.chmod(0o755)

    def test_container_scan_fails_on_unreadable_dir(self):
        proc = self.scan(CONTAINER_SCAN, "services", "FROM alpine\n")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("could not list", proc.stderr)

    def test_tf_scan_fails_on_unreadable_dir(self):
        proc = self.scan(TF_SCAN, "infra/locked", 'variable "x" {}\n')
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("could not list", proc.stderr)

    def scan_with_locked_excluded(self, script: Path, excluded: str) -> subprocess.CompletedProcess:
        """A readable target file plus an unreadable directory the scan excludes."""
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp, "proj")
            proj.mkdir()
            if script == CONTAINER_SCAN:
                (proj / "Dockerfile").write_text("FROM alpine:3.20\nUSER app\n")
                (proj / ".dockerignore").write_text(".git\n")
            else:
                (proj / "main.tf").write_text('variable "x" {}\n')
            locked = proj / excluded / "pkg"
            locked.mkdir(parents=True)
            (locked / ("Dockerfile" if script == CONTAINER_SCAN else "main.tf")).write_text("x\n")
            (proj / excluded).chmod(0)
            try:
                return run(script, proj, BASE_PATH)
            finally:
                (proj / excluded).chmod(0o755)

    def test_container_scan_prunes_unreadable_excluded_dirs(self):
        for excluded in ("node_modules", ".venv", ".git", "svc/node_modules"):
            with self.subTest(excluded=excluded):
                proc = self.scan_with_locked_excluded(CONTAINER_SCAN, excluded)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_tf_scan_prunes_unreadable_excluded_dirs(self):
        for excluded in (".terraform", "infra/.terraform", "node_modules", ".venv", ".git"):
            with self.subTest(excluded=excluded):
                proc = self.scan_with_locked_excluded(TF_SCAN, excluded)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
