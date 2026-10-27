#!/usr/bin/env python3
"""Unit tests for coverage-ratchet.py exit codes and the TST-RATCHET verification cmd."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RATCHET = ROOT / "checks" / "coverage-ratchet.py"
_fm = re.match(r"\A---\n(.*?)\n---\n",
               (ROOT / "standards" / "testing" / "tst-ratchet.md").read_text(), re.DOTALL)
RATCHET_CMD = next(str(v["cmd"]) for v in yaml.safe_load(_fm.group(1))["verification"]
                   if "coverage-ratchet.py" in str(v["cmd"]))


def run_cmd(project: Path, gov: Path) -> int:
    return subprocess.run(["bash", "-c", RATCHET_CMD], cwd=project,
                          env={**os.environ, "GOVERNANCE_DIR": str(gov)},
                          capture_output=True, check=False).returncode


def write_coverage(project: Path, pct: float) -> None:
    (project / "coverage.json").write_text(json.dumps({"totals": {"percent_covered": pct}}))


class RatchetExitCodeTests(unittest.TestCase):
    def test_no_data_exits_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(RATCHET), "--check"], cwd=tmp,
                                  capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 3, proc.stdout)


class RatchetVerificationCmdTests(unittest.TestCase):
    def test_no_data_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_cmd(Path(tmp), ROOT), 0)

    def test_missing_script_fails(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as gov:
            self.assertNotEqual(run_cmd(Path(tmp), Path(gov)), 0)

    def test_below_baseline_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".coverage-baseline").write_text("80.00\n")
            write_coverage(project, 50.0)
            self.assertNotEqual(run_cmd(project, ROOT), 0)

    def test_at_baseline_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".coverage-baseline").write_text("80.00\n")
            write_coverage(project, 80.0)
            self.assertEqual(run_cmd(project, ROOT), 0)


if __name__ == "__main__":
    unittest.main()
