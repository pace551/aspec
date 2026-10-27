#!/usr/bin/env python3
"""Tests for run-verification.py pin enforcement (ADR-0004), against a throwaway
governance dir holding one fake standard at version 1.2.3 whose only check is `true`."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).with_name("run-verification.py")
spec = importlib.util.spec_from_file_location("run_verification", VERIFY)
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)

STANDARD = """---
id: TST-FAKE
version: 1.2.3
verification:
  - cmd: "true"
    expect: "exit 0"
    layer: G
    rules: [TST-FAKE-01]
---
"""


def verify(pinned: str) -> dict:
    with tempfile.TemporaryDirectory() as gov, tempfile.TemporaryDirectory() as proj:
        (Path(gov) / "standards" / "testing").mkdir(parents=True)
        (Path(gov) / "standards" / "testing" / "tst-fake.md").write_text(STANDARD)
        Path(proj, "GOVERNANCE.md").write_text(
            "```yaml\ntier: T1\nstandards:\n"
            f"  - {{id: TST-FAKE, version: {pinned}}}\nwaivers: []\n```\n")
        proc = subprocess.run(
            [sys.executable, str(VERIFY), "--project", proj, "--governance-dir", gov,
             "--json"], capture_output=True, text=True, check=False)
    report = json.loads(proc.stdout)
    report["exit"] = proc.returncode
    report["ran_check"] = any(r["kind"] == "check" for r in report["results"])
    report["pin"] = next((r for r in report["results"] if r["kind"] == "standard"), None)
    return report


DRIFT_CASES = (
    ("1.2.3", "1.2.3", None),
    ("1.2.1", "1.2.3", "WARN"),
    ("1.1.9", "1.2.3", "FAIL"),
    ("0.9.0", "1.2.3", "FAIL"),
    ("1.2.4", "1.2.3", "FAIL"),
    ("1.3.0", "1.2.3", "FAIL"),
    ("2.0.0", "1.2.3", "FAIL"),
    ("1.2", "1.2.3", "FAIL"),
    ("", "1.2.3", "FAIL"),
    ("1.2.10", "1.2.9", "FAIL"),
    ("1.2.9", "1.2.10", "WARN"),
    ("1.2.3\n", "1.2.4", "FAIL"),
    ("1.2.3\n", "1.2.3\n", "FAIL"),
    ("", "", "FAIL"),
    ("latest", "latest", "FAIL"),
    ("1.2.\u0663", "1.2.3", "FAIL"),
)


class PinDriftTests(unittest.TestCase):
    def test_levels(self):
        for pinned, current, expected in DRIFT_CASES:
            with self.subTest(pinned=pinned, current=current):
                drift = rv.pin_drift(pinned, current)
                self.assertEqual(drift and drift[0], expected)


class VerifierPinTests(unittest.TestCase):
    def test_exact_pin_passes(self):
        r = verify("1.2.3")
        self.assertEqual((r["exit"], r["pin"], r["ran_check"]), (0, None, True))

    def test_patch_drift_warns_and_runs_checks(self):
        r = verify("1.2.1")
        self.assertEqual((r["exit"], r["pin"]["status"], r["ran_check"]), (0, "WARN", True))

    def test_minor_drift_fails_without_running_checks(self):
        r = verify("1.1.0")
        self.assertEqual((r["exit"], r["pin"]["status"], r["ran_check"]),
                         (1, "FAIL", False))
        self.assertIn("re-run /govern", r["pin"]["detail"])

    def test_major_drift_fails(self):
        r = verify("0.9.0")
        self.assertEqual((r["exit"], r["pin"]["status"], r["ran_check"]),
                         (1, "FAIL", False))

    def test_pin_newer_than_repo_fails(self):
        r = verify("1.2.4")
        self.assertEqual((r["exit"], r["pin"]["status"], r["ran_check"]),
                         (1, "FAIL", False))
        self.assertIn("update the governance repo", r["pin"]["detail"])


if __name__ == "__main__":
    unittest.main()
