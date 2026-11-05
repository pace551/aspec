#!/usr/bin/env python3
"""Tests that ASPEC's own scripts run on the governance repo's .venv, never a bare python3.

The skills and the standards' verification commands used to launch checks/*.py with the
system `python3`, which can be an end-of-life Python (3.9 on macOS) that no test covers.
checks/install.sh now builds $GOVERNANCE_DIR/.venv (Python 3.11+, the `runtime` dependency
group), everything launches through it, and lint-framework rejects a bare `python3`.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "checks" / "install.sh"
spec = importlib.util.spec_from_file_location(
    "lint_framework", ROOT / "checks" / "lint-framework.py"
)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

BARE = [
    'python3 "$GOVERNANCE_DIR/checks/coverage-ratchet.py" --check',
    "sh -c 'go test ./...; python3 \"$GOVERNANCE_DIR/checks/coverage-ratchet.py\" --check'",
    "python3 $GOV/checks/run-verification.py --project .",
    "python3.9 ${GOVERNANCE_DIR}/checks/import-cycles.py",
    "python $GOV/checks/select-standards.py --tier T1",
]
ALLOWED = [
    '"$GOVERNANCE_DIR/.venv/bin/python" "$GOVERNANCE_DIR/checks/coverage-ratchet.py" --check',
    "$GOV/.venv/bin/python $GOV/checks/run-verification.py --project .",
    "python3 .governance/coverage-ratchet.py --check",  # a project's vendored copy
    'bash "$GOVERNANCE_DIR/checks/secret-scan.sh"',
]


class GuardTests(unittest.TestCase):
    def test_bare_python_is_flagged(self):
        for text in BARE:
            with self.subTest(text=text):
                self.assertTrue(lint.bare_python_launch(text))

    def test_venv_python_and_vendored_copies_pass(self):
        for text in ALLOWED:
            with self.subTest(text=text):
                self.assertFalse(lint.bare_python_launch(text))


class CorpusTests(unittest.TestCase):
    def test_standards_launch_checks_through_the_venv(self):
        for path in sorted((ROOT / "standards").rglob("*.md")):
            text = path.read_text()
            front = yaml.safe_load(re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL).group(1))
            for v in front["verification"]:
                with self.subTest(path=path.name, cmd=v["cmd"][:60]):
                    self.assertFalse(lint.bare_python_launch(str(v["cmd"])))
            with self.subTest(path=path.name, part="body"):
                self.assertFalse(lint.bare_python_launch(text))

    def test_skills_launch_checks_through_the_venv(self):
        for path in sorted((ROOT / "skills").rglob("SKILL.md")):
            with self.subTest(path=path.parent.name):
                self.assertFalse(lint.bare_python_launch(path.read_text()))


class VendoredRatchetTests(unittest.TestCase):
    """coverage-ratchet.py is copied into projects and run by their python3, not the venv."""

    SCRIPT = ROOT / "checks" / "coverage-ratchet.py"

    def test_parses_as_python_3_9(self):
        import ast

        ast.parse(self.SCRIPT.read_text(), feature_version=(3, 9))

    def test_runs_on_python_3_9_when_available(self):
        py39 = next((p for p in ("python3.9", "/usr/bin/python3") if _is_39(p)), None)
        if py39 is None:
            self.skipTest("no Python 3.9 interpreter here")
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "coverage.json").write_text('{"totals": {"percent_covered": 80.0}}')
            Path(tmp, ".coverage-baseline").write_text("75\n")
            proc = subprocess.run(
                [py39, str(self.SCRIPT), "--check"],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)


def _is_39(python: str) -> bool:
    try:
        out = subprocess.run(
            [python, "-c", "import sys; print(sys.version_info[:2])"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except FileNotFoundError:
        return False
    return out.strip() == "(3, 9)"


def install(home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(INSTALL)],
        input="none\n",
        env={**os.environ, "HOME": str(home)},
        capture_output=True,
        text=True,
        check=False,
    )


class InstallVenvTests(unittest.TestCase):
    def test_existing_usable_venv_is_kept(self):
        python = ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            self.skipTest("no repo .venv (create it per CLAUDE.md)")
        before = python.resolve().stat().st_mtime
        with tempfile.TemporaryDirectory() as tmp:
            proc = install(Path(tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("governance venv: ok, synced to the runtime group", proc.stdout)
        self.assertEqual(python.resolve().stat().st_mtime, before)

    def test_installed_skills_point_at_the_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual(install(home).returncode, 0)
            text = (home / ".claude" / "skills" / "govern" / "SKILL.md").read_text()
        self.assertIn(f"{ROOT}/.venv/bin/python {ROOT}/checks/select-standards.py", text)


if __name__ == "__main__":
    unittest.main()
