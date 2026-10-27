#!/usr/bin/env python3
"""Unit tests for select-standards.py trigger matching (whole word + endings)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

SELECT = Path(__file__).with_name("select-standards.py")
spec = importlib.util.spec_from_file_location("select_standards", SELECT)
sel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sel)

HITS = [
    ("ci", "set up ci for the repo"),
    ("ci", "add a ci/cd pipeline"),
    ("pr", "open a pr against main"),
    ("tag", "tag v2.1.0 and publish"),
    ("pr", "review open prs"),
    ("deploy", "we deployed it yesterday"),
    ("deploy", "deploying to prod"),
    ("retry", "add retries with backoff"),
    ("cache", "enable prompt caching"),
    ("test", "improve testing"),
    ("ship", "before shipping to users"),
    ("rotate", "rotating the keys"),
    ("stripe", "add stripe payments"),
    ("api key", "rotate the api keys monthly"),
    (".env", "load secrets from .env"),
    ("n+1", "fix the n+1 query"),
    ("next.js", "a next.js app"),
]
MISSES = [
    ("ci", "we decided to wait"),
    ("tag", "stage the release"),
    ("sha", "share the report"),
    ("pr", "write a prompt"),
    ("pr", "the product page"),
    ("ses", "paginated responses"),
    ("rds", "restore the deleted records"),
    ("form", "add a terraform module"),
    ("form", "format the dates"),
    ("rest", "restart the worker"),
    ("prod", "the product page"),
    ("gate", "investigate the failure"),
    ("rag", "raise coverage"),
    ("token", "tokenize the csv"),
    ("go", "we are going to add it"),
    ("pip", "piping data between jobs"),
    ("rag", "ragged edges"),
    ("waf", "a silicon wafer"),
    ("react", "a chemical reaction"),
    ("secret", "gland secretion"),
    ("commit", "a long-term commitment"),
    ("ship", "track the shipment"),
    ("form", "the former owner"),
    ("toast", "a new toaster"),
    ("deploy", "fix the deployment script"),
]


class TriggerRegexTests(unittest.TestCase):
    def test_hits(self):
        for trigger, brief in HITS:
            with self.subTest(trigger=trigger, brief=brief):
                self.assertTrue(sel.trigger_re(trigger).search(brief))

    def test_misses(self):
        for trigger, brief in MISSES:
            with self.subTest(trigger=trigger, brief=brief):
                self.assertFalse(sel.trigger_re(trigger).search(brief))


def triggered(tier: str, brief: str) -> dict[str, str]:
    proc = subprocess.run(
        [sys.executable, str(SELECT), "--tier", tier, "--brief-text", brief],
        capture_output=True, text=True, check=True)
    return {s["id"]: s["matched_on"] for s in json.loads(proc.stdout)["selected"]
            if s["matched_on"].startswith("triggers")}


class SelectionTests(unittest.TestCase):
    def test_embedded_short_triggers_no_longer_select(self):
        got = triggered("T2", "We decided to stage it; share the product notes")
        self.assertNotIn("DEV-CI", got)
        self.assertNotIn("OPS-RELEASE", got)
        self.assertNotIn("SEC-CRYPTO", got)

    def test_whole_word_triggers_still_select(self):
        got = triggered("T2", "Set up CI and tag the release")
        self.assertIn("ci", got.get("DEV-CI", ""))
        self.assertIn("tag", got.get("OPS-RELEASE", ""))

    def test_brand_trigger_selects(self):
        got = triggered("T3", "Integrate Stripe")
        self.assertIn("stripe", got.get("LEG-COMMERCIAL", ""))

    def test_whitespace_in_brief_does_not_break_phrases(self):
        got = triggered("T2", "add a health\n   checks endpoint")
        self.assertIn("health check", got.get("OPS-ALERTS", ""))


if __name__ == "__main__":
    unittest.main()
