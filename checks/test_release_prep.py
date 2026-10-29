#!/usr/bin/env python3
"""Unit tests for release-prep.py: LICENSE Change Date bump and CHANGELOG release heading."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREP = ROOT / "checks" / "release-prep.py"

LICENSE = """Business Source License 1.1

Parameters

Additional Use Grant: You may use the Licensed Work.
Change Date:          2029-10-28
Change License:       MIT
"""

CHANGELOG = """# Changelog — ASPEC

Intro text.

## Unreleased

- Entry one.
- Entry two.

## 0.1.0 — 2026-07-22

- Initial framework build.
"""


def make_repo(tmp: Path, version: str = "0.2.0", changelog: str = CHANGELOG,
              license_text: str = LICENSE) -> Path:
    (tmp / "LICENSE").write_text(license_text)
    (tmp / "CHANGELOG.md").write_text(changelog)
    (tmp / ".release-please-manifest.json").write_text(json.dumps({".": version}))
    return tmp


def run(tmp: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(PREP), "--root", str(tmp), *args],
                          capture_output=True, text=True, check=False)


class PrepareTests(unittest.TestCase):
    def test_change_date_is_release_date_plus_three_years(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t))
            proc = run(tmp, "prepare", "--date", "2026-11-03")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Change Date:          2029-11-03\n", (tmp / "LICENSE").read_text())

    def test_leap_day_release_maps_to_feb_28(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t))
            proc = run(tmp, "prepare", "--date", "2028-02-29")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Change Date:          2031-02-28\n", (tmp / "LICENSE").read_text())

    def test_unreleased_entries_move_under_version_heading(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t))
            run(tmp, "prepare", "--date", "2026-11-03")
            text = (tmp / "CHANGELOG.md").read_text()
            self.assertIn("## Unreleased\n\n## 0.2.0 — 2026-11-03\n\n- Entry one.\n- Entry two.\n"
                          "\n## 0.1.0 — 2026-07-22\n", text)

    def test_rerun_is_idempotent_and_refreshes_date(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t))
            run(tmp, "prepare", "--date", "2026-11-03")
            proc = run(tmp, "prepare", "--date", "2026-11-05")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = (tmp / "CHANGELOG.md").read_text()
            self.assertEqual(text.count("## 0.2.0"), 1)
            self.assertIn("## 0.2.0 — 2026-11-05\n\n- Entry one.", text)
            self.assertIn("Change Date:          2029-11-05\n", (tmp / "LICENSE").read_text())

    def test_refuses_to_fold_entries_into_an_existing_version_section(self):
        # e.g. run by hand on main, where the manifest still names the released version
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t), version="0.1.0")
            proc = run(tmp, "prepare", "--date", "2026-11-03")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("0.1.0", proc.stderr)
            self.assertEqual((tmp / "CHANGELOG.md").read_text(), CHANGELOG)
            self.assertEqual((tmp / "LICENSE").read_text(), LICENSE)

    def test_missing_change_date_line_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t), license_text="Business Source License 1.1\n")
            proc = run(tmp, "prepare", "--date", "2026-11-03")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("Change Date", proc.stderr)

    def test_missing_unreleased_heading_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t), changelog="# Changelog\n\n## 0.1.0 — 2026-07-22\n")
            proc = run(tmp, "prepare", "--date", "2026-11-03")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("Unreleased", proc.stderr)

    def test_failure_leaves_files_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t), changelog="# Changelog\n")
            run(tmp, "prepare", "--date", "2026-11-03")
            self.assertEqual((tmp / "LICENSE").read_text(), LICENSE)


class NotesTests(unittest.TestCase):
    def test_prints_the_version_section_body(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t))
            run(tmp, "prepare", "--date", "2026-11-03")
            proc = run(tmp, "notes", "0.2.0")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout, "- Entry one.\n- Entry two.\n")

    def test_unknown_version_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = make_repo(Path(t))
            proc = run(tmp, "notes", "9.9.9")
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
