#!/usr/bin/env python3
"""Unit tests for lint-framework.py hardcoded-path detection."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import yaml

spec = importlib.util.spec_from_file_location(
    "lint_framework", Path(__file__).with_name("lint-framework.py"))
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

CMD_HITS = [
    "bash /opt/aspec/checks/sec-sast.sh",
    "bash /tmp/aspec/hooks/pre-write-secret-scan.sh",
    'python3 "/workspace/aspec/checks/coverage-ratchet.py" --check',
    "sh -c 'pytest; python3 /srv/aspec/checks/coverage-ratchet.py --check'",
    "bash ~/x/checks/a.sh",
    "bash $HOME/aspec/checks/a.sh",
]
CMD_MISSES = [
    'bash "$GOVERNANCE_DIR/checks/secret-scan.sh"',
    'bash "${GOVERNANCE_DIR}/checks/x.sh" --tier T3',
    "go test ./... >/dev/null 2>&1",
    "sh -c '[ -x .git/hooks/pre-commit ]'",
    "python3 .governance/coverage-ratchet.py --check",
    "/usr/bin/env python3 -V",
]
BODY_HITS = [
    "`bash /opt/aspec/checks/sec-sast.sh`",
    "cp /srv/aspec/templates/scaffolds/_common/x .",
    "`bash ~/Dev/x/checks/foo.sh`",
]
BODY_MISSES = [
    "https://github.com/org/repo/blob/main/checks/x.py",
    "POST /api/hooks/stripe",
    "`~/Library/Logs/mytool/`",
    '"$HOME/Dev/mytool/.venv/bin/python" -m mytool',
    'bash "$GOVERNANCE_DIR/templates/scaffolds/_common/install-git-hooks.sh"',
]


class CmdPathTests(unittest.TestCase):
    def test_hits(self):
        for cmd in CMD_HITS:
            with self.subTest(cmd=cmd):
                self.assertTrue(lint.hardcoded_cmd_path(cmd))

    def test_misses(self):
        for cmd in CMD_MISSES:
            with self.subTest(cmd=cmd):
                self.assertFalse(lint.hardcoded_cmd_path(cmd))


class BodyPathTests(unittest.TestCase):
    def test_hits(self):
        for body in BODY_HITS:
            with self.subTest(body=body):
                self.assertTrue(lint.hardcoded_body_path(body))

    def test_misses(self):
        for body in BODY_MISSES:
            with self.subTest(body=body):
                self.assertFalse(lint.hardcoded_body_path(body))


class CorpusTests(unittest.TestCase):
    def test_no_hardcoded_paths_in_corpus(self):
        root = Path(__file__).resolve().parent.parent
        for path in sorted((root / "standards").rglob("*.md")):
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                m = lint.FRONTMATTER_RE.match(text)
                self.assertIsNotNone(m)
                meta = yaml.safe_load(m.group(1))
                for v in meta.get("verification") or []:
                    cmd = str(v["cmd"])
                    self.assertFalse(
                        lint.hardcoded_cmd_path(cmd),
                        f"{path.name} cmd: {cmd}")
                self.assertFalse(
                    lint.hardcoded_body_path(text[m.end():]),
                    f"{path.name} body")


if __name__ == "__main__":
    unittest.main()
