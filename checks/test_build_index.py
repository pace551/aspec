#!/usr/bin/env python3
"""Unit tests for build-index.py's version gate (Constitution C10).

A standard's content can't change without a `version` bump, a bump must come with a new
`last_review` date, and a `last_review`-only touch (the /evolve-standards staleness sweep)
needs no bump. Each test runs a copy of the script against its own standards tree.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-11-05"  # passed to build-index, so no test reads the clock
SCRIPT = ROOT / "checks" / "build-index.py"

STANDARD = """---
id: TST-DEMO
title: Demo
family: TST
version: {version}
status: active
tiers: {{T1: advisory, T2: required, T3: required, T4: required}}
stacks: all
triggers: [demo]
requires: []
verification: []
last_review: {last_review}
---

# Demo

{body}
"""


class BuildIndexGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "checks").mkdir()
        (self.root / "standards" / "testing").mkdir(parents=True)
        self.path = self.root / "standards" / "testing" / "tst-demo.md"
        self.hashes = self.root / "checks" / ".index-hashes.json"

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, version="1.0.0", last_review="2026-07-22", body="Original."):
        self.path.write_text(
            STANDARD.format(version=version, last_review=last_review, body=body),
            encoding="utf-8",
        )

    def build(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), "--today", TODAY],
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_built(self):
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def assert_refused(self, needle: str):
        r = self.build()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(needle, r.stdout)

    def test_unchanged_standard_builds(self):
        self.write()
        self.assert_built()
        self.assert_built()

    def test_content_change_without_bump_is_refused(self):
        self.write()
        self.assert_built()
        self.write(body="Edited.")
        self.assert_refused("content changed but version still 1.0.0")

    def test_bump_with_new_last_review_builds(self):
        self.write()
        self.assert_built()
        self.write(version="1.0.1", last_review="2026-11-05", body="Edited.")
        self.assert_built()

    def test_bump_without_new_last_review_is_refused(self):
        self.write()
        self.assert_built()
        self.write(version="1.0.1", body="Edited.")
        self.assert_refused("version changed to 1.0.1 but last_review 2026-07-22")

    def test_bump_with_an_earlier_last_review_is_refused(self):
        self.write()
        self.assert_built()
        self.write(version="1.0.1", last_review="2026-07-21", body="Edited.")
        self.assert_refused("version changed to 1.0.1 but last_review 2026-07-21")

    def test_same_day_bump_after_a_sweep_builds(self):
        # indexed long ago; today's sweep touches last_review alone; a later edit the same
        # day bumps the version and keeps today's date
        self.write()
        self.assert_built()
        self.write(last_review=TODAY)
        self.assert_built()
        self.write(version="1.0.1", last_review=TODAY, body="Edited.")
        self.assert_built()

    def test_bump_with_a_future_last_review_is_refused(self):
        self.write()
        self.assert_built()
        self.write(version="1.0.1", last_review="2099-01-01", body="Edited.")
        self.assert_refused("last_review 2099-01-01 is after today")

    def test_new_standard_with_a_future_last_review_is_refused(self):
        self.write(last_review="2099-01-01")
        self.assert_refused("last_review 2099-01-01 is after today")

    def test_last_review_a_day_ahead_builds(self):
        # an author east of UTC is a day ahead of a UTC CI runner
        self.write(last_review="2026-11-06")
        self.assert_built()

    def test_same_day_bump_after_a_day_ahead_review_builds(self):
        self.write()
        self.assert_built()
        self.write(version="1.0.1", last_review="2026-11-06", body="Edited.")
        self.assert_built()
        self.write(version="1.0.2", last_review="2026-11-06", body="Edited again.")
        self.assert_built()

    def test_last_review_must_be_a_date(self):
        self.write(last_review="TBD")
        self.assert_refused("last_review 'TBD' is not a YYYY-MM-DD date")

    def test_today_must_be_a_date(self):
        self.write()
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), "--today", "2026-11-5"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_generated_date_is_today(self):
        self.write()
        self.assert_built()
        index = json.loads((self.root / "index.json").read_text())
        self.assertEqual(index["generated"], TODAY)

    def test_last_review_only_touch_needs_no_bump(self):
        # /evolve-standards step 4: a standard that is still fine gets last_review: today
        # and nothing else, and that edit is exempt from a version bump.
        self.write()
        self.assert_built()
        self.write(last_review="2026-11-05")
        self.assert_built()

    def test_last_review_touch_with_other_edits_still_needs_bump(self):
        self.write()
        self.assert_built()
        self.write(last_review="2026-11-05", body="Edited.")
        self.assert_refused("content changed but version still 1.0.0")

    def test_legacy_hashes_file_is_read(self):
        # Hashes written before last_review was recorded: whole-file sha256 and no
        # last_review key. An unchanged standard must still build, an edit must still be
        # refused, and a bump is accepted whatever its last_review (no prior date known).
        self.write()
        self.assert_built()
        legacy = {
            sid: {"version": e["version"], "hash": self._whole_file_hash()}
            for sid, e in json.loads(self.hashes.read_text()).items()
        }
        self.hashes.write_text(json.dumps(legacy))
        self.assert_built()
        self.assertIn("last_review", json.loads(self.hashes.read_text())["TST-DEMO"])

        self.hashes.write_text(json.dumps(legacy))
        self.write(body="Edited.")
        self.assert_refused("content changed but version still 1.0.0")

        self.write(version="1.0.1", body="Edited.")
        self.assert_built()

    def _whole_file_hash(self) -> str:
        import hashlib

        return hashlib.sha256(self.path.read_text(encoding="utf-8").encode()).hexdigest()


if __name__ == "__main__":
    unittest.main()
