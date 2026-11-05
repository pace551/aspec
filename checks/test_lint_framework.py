#!/usr/bin/env python3
"""Unit tests for lint-framework.py hardcoded-path detection."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import yaml

spec = importlib.util.spec_from_file_location(
    "lint_framework", Path(__file__).with_name("lint-framework.py")
)
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
                    self.assertFalse(lint.hardcoded_cmd_path(cmd), f"{path.name} cmd: {cmd}")
                self.assertFalse(lint.hardcoded_body_path(text[m.end() :]), f"{path.name} body")


class ReferenceIntegrityTests(unittest.TestCase):
    """Docs, skills and standards must not name framework files or ADRs that don't exist,
    nor tell a user to pip-install a package the toolchain doesn't pin."""

    ROOT = Path(__file__).resolve().parent.parent

    def test_dangling_framework_paths_are_flagged(self):
        for text in (
            "run `checks/no-such-script.sh` first",
            "copy $GOV/templates/ci/cobol.yml",
            'bash "$GOVERNANCE_DIR/checks/gone.py"',
            "see skills/no-such-skill/SKILL.md.",
            "decided in ADR-0099",
            'bash "$GOVERNANCE_DIR"/checks/gone.sh',
            "copy checks/test_gone*.py",
        ):
            with self.subTest(text=text):
                self.assertTrue(lint.dangling_refs(text, self.ROOT), text)

    def test_existing_and_placeholder_paths_pass(self):
        for text in (
            "run `checks/secret-scan.sh`, then checks/build-index.py.",
            "copy $GOV/templates/ci/python.yml to .github/workflows/ci.yml",
            "templates/scaffolds/{stack}/ and templates/ci/<stack>.yml",
            "skills/govern/SKILL.md and ADR-0005",
            "a project's own scripts/deploy.sh or docs/threat-model.md",
            "https://github.com/pace551/aspec/blob/main/checks/x.py",
            "run checks/test_*.py and checks/verify-{name}.sh",
            "run checks/test_?????_*.py or checks/test_[a-z]*.py",
            "Did you run checks/install.sh? Then checks/secret-scan.sh?",
            "a one-character glob: checks/install.s?",
            "[raw](https://x.invalid/checks/a.sh) and [link](../checks/install.sh?raw=1)",
            "render templates/email/receipt.html or skills/ in the project",
        ):
            with self.subTest(text=text):
                self.assertEqual(lint.dangling_refs(text, self.ROOT), [], text)

    def test_relative_links_resolve_from_their_file(self):
        doc = self.ROOT / "docs" / "GUIDE.md"
        self.assertEqual(lint.dangling_refs("[x](../checks/secret-scan.sh)", self.ROOT, doc), [])
        self.assertEqual(
            lint.dangling_refs("[x](../checks/gone.sh)", self.ROOT, doc), ["checks/gone.sh"]
        )
        self.assertEqual(
            lint.dangling_refs("[x](../checks/deleted*.py)", self.ROOT, doc), ["checks/deleted*.py"]
        )
        self.assertEqual(lint.dangling_refs("[x](../checks/test_*.py)", self.ROOT, doc), [])

    def test_adrs_are_checked_outside_standards_only(self):
        std = self.ROOT / "standards" / "process" / "dev-adr.md"
        skill = self.ROOT / "skills" / "govern" / "SKILL.md"
        self.assertEqual(lint.dangling_refs("record it as ADR-0099", self.ROOT, std), [])
        self.assertEqual(lint.dangling_refs("see ADR-0099", self.ROOT, skill), ["ADR-0099"])

    def test_pip_installs_must_name_pinned_packages(self):
        pinned = {"pyyaml", "ruff"}
        clean = [
            "`pip install -q pyyaml ruff`",
            "```\npython3 -m pip install --group dev\n```",
            "no manual <code>pip install</code>",
            "`pip3 install PyYAML==6.0.3`",
            '<pre>pip install "ruff" \\\n  (pyyaml)</pre>',
            "`pip install --upgrade pip`",
            "`pip install pyyaml && echo ready`",
            "`pip install ruff; ruff check .`",
            "pip install ruff and then run it",  # prose isn't a command: only code is read
        ]
        for text in clean:
            with self.subTest(text=text):
                self.assertEqual(lint.unpinned_pip_installs(text, pinned), [])
        self.assertEqual(
            lint.unpinned_pip_installs("`pip install pyyaml flake8`", pinned), ["flake8"]
        )
        marker = "`pip install \"ruff; python_version >= '3.11'\" flake8`"
        self.assertEqual(lint.unpinned_pip_installs(marker, pinned), ["flake8"])
        marked = "`pip install \"flake8; python_version >= '3.11'\"`"
        self.assertEqual(lint.unpinned_pip_installs(marked, pinned), ["flake8"])

    def test_pyproject_packages_are_read(self):
        pinned = lint.pyproject_packages(self.ROOT)
        self.assertIn("pyyaml", pinned)
        self.assertIn("ruff", pinned)

    def test_the_framework_has_no_dangling_references(self):
        for path in lint.reference_files(self.ROOT):
            with self.subTest(path=str(path.relative_to(self.ROOT))):
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertEqual(lint.dangling_refs(text, self.ROOT, path), [])


if __name__ == "__main__":
    unittest.main()
