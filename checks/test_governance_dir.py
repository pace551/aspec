#!/usr/bin/env python3
"""Unit tests for GOVERNANCE_DIR resolution in the check scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env() -> dict:
    """Literal-tilde GOVERNANCE_DIR under a changed HOME (only expanduser resolves it)."""
    env = {**os.environ,
           "HOME": str(ROOT.parent),
           "GOVERNANCE_DIR": f"~/{ROOT.name}"}
    probe = subprocess.run([sys.executable, "-c", "import yaml"],
                           env=env, capture_output=True, check=False)
    if probe.returncode != 0:
        import yaml
        env["PYTHONPATH"] = str(Path(yaml.__file__).resolve().parent.parent)
    return env


class GovernanceDirTests(unittest.TestCase):
    def test_select_standards_tilde_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "checks/select-standards.py"),
                 "--tier", "T1"],
                cwd=tmp, env=_env(), capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["selected"])

    def test_run_verification_tilde_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "GOVERNANCE.md").write_text(
                "# Governance Manifest\n\n```yaml\ntier: T1\nstandards: []\n"
                "waivers: []\n```\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "checks/run-verification.py"),
                 "--project", tmp, "--json"],
                cwd=tmp, env=_env(), capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["passed"])

    def test_select_standards_bad_dir_fails_loudly(self):
        env = _env()
        env["GOVERNANCE_DIR"] = "/nonexistent"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "checks/select-standards.py"),
             "--tier", "T1"],
            env=env, capture_output=True, text=True, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("is not an ASPEC repo", proc.stderr)


if __name__ == "__main__":
    unittest.main()
