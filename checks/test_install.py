#!/usr/bin/env python3
"""Tests for checks/install.sh against a throwaway HOME (never the real ~/.claude)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "checks" / "install.sh"


def install(home: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(INSTALL), *flags], input="none\n",
                          env={**os.environ, "HOME": str(home)},
                          capture_output=True, text=True, check=False)


class InstallTests(unittest.TestCase):
    def test_fresh_home_without_claude_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            proc = install(home, "--hooks", "--global-claude")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            config = json.loads((home / ".claude" / "aspec.json").read_text())
            self.assertEqual(config["governance_repo"], str(ROOT))
            self.assertTrue((home / ".claude" / "skills" / "govern" / "SKILL.md").is_file())
            self.assertTrue((home / ".claude" / "CLAUDE.md").is_file())
            settings = json.loads((home / ".claude" / "settings.json").read_text())
            self.assertIn("PreToolUse", settings["hooks"])
            self.assertEqual(list((home / ".claude").glob("settings.json.bak.*")), [])

    def test_existing_settings_are_backed_up_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir()
            (home / ".claude" / "settings.json").write_text('{"model": "x"}\n')
            proc = install(home, "--hooks")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            settings = json.loads((home / ".claude" / "settings.json").read_text())
            self.assertEqual(settings["model"], "x")
            self.assertIn("SessionStart", settings["hooks"])
            self.assertEqual(len(list((home / ".claude").glob("settings.json.bak.*"))), 1)


if __name__ == "__main__":
    unittest.main()
