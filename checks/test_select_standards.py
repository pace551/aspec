#!/usr/bin/env python3
"""Unit tests for select-standards.py stack-key validation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELECT = ROOT / "checks" / "select-standards.py"
KEYS = json.loads((ROOT / "checks" / "stack-keys.json").read_text())


def select(stacks: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SELECT), "--tier", "T3", "--stacks", stacks],
        capture_output=True,
        text=True,
        check=False,
    )


def selected_ids(proc: subprocess.CompletedProcess) -> set[str]:
    return {s["id"] for s in json.loads(proc.stdout)["selected"]}


class StackKeyTests(unittest.TestCase):
    def test_unknown_key_is_usage_error(self):
        proc = select("python,postgres")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("unknown stack key(s): postgres", proc.stderr)
        self.assertIn("postgresql", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_all_unknown_keys_reported(self):
        proc = select("pythn,dynamo,python")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown stack key(s): dynamo, pythn", proc.stderr)

    def test_valid_store_keys_select_required_standards(self):
        proc = select("python,postgresql,dynamodb")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue({"STK-PG", "STK-DDB"} <= selected_ids(proc))

    def test_every_canonical_key_accepted(self):
        self.assertEqual(select(",".join(KEYS)).returncode, 0)

    def test_empty_stacks_accepted(self):
        self.assertEqual(select("").returncode, 0)


class LlmStackTests(unittest.TestCase):
    """ADR-0006: detecting the llm stack pins AI-EVALS at T1 with no trigger word."""

    def pins(self, stacks: str) -> set[str]:
        proc = subprocess.run(
            [
                sys.executable,
                str(SELECT),
                "--tier",
                "T1",
                "--stacks",
                stacks,
                "--brief-text",
                "personal inbox triage tool",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return selected_ids(proc)

    def test_llm_stack_pins_ai_evals_at_t1(self):
        self.assertIn("AI-EVALS", self.pins("python,llm"))

    def test_no_llm_stack_no_ai_evals(self):
        self.assertNotIn("AI-EVALS", self.pins("python"))


class StackKeySourceTests(unittest.TestCase):
    def test_every_standard_stack_is_canonical(self):
        index = json.loads((ROOT / "index.json").read_text())
        used = {s for e in index["standards"] if e["stacks"] != "all" for s in e["stacks"]}
        self.assertLessEqual(used, set(KEYS))

    def test_authoring_doc_lists_canonical_keys(self):
        text = (ROOT / "templates" / "AUTHORING.md").read_text()
        item = re.search(r"8\. \*\*Stack keys vocabulary\*\*(.*?)\n9\. ", text, re.DOTALL)
        self.assertIsNotNone(item)
        documented = set(re.findall(r"`([a-z][a-z-]*)`", item.group(1))) - {"all"}
        self.assertEqual(documented, set(KEYS))


if __name__ == "__main__":
    unittest.main()
