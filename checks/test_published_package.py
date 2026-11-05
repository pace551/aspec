#!/usr/bin/env python3
"""Tests for the published-package carve-out (ADR-0005): the `published` frontmatter key
(lint), `--published` in select-standards.py, and `published_package` in
run-verification.py, plus the corpus matching ADR-0005's classification table."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SELECT = ROOT / "checks" / "select-standards.py"
VERIFY = ROOT / "checks" / "run-verification.py"
spec = importlib.util.spec_from_file_location(
    "lint_framework", ROOT / "checks" / "lint-framework.py"
)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

TIERS_T3_UP = {"T1": "advisory", "T2": "advisory", "T3": "required", "T4": "required"}


def entry(sid: str, published: str, tiers: dict | None = None) -> dict:
    return {
        "id": sid,
        "title": sid,
        "version": "1.0.0",
        "status": "active",
        "path": f"standards/x/{sid.lower()}.md",
        "tiers": tiers or TIERS_T3_UP,
        "stacks": "all",
        "triggers": [sid.lower()],
        "requires": [],
        "published": published,
    }


def select(*args: str, index: tuple[dict, ...] | list[dict]) -> dict:
    with tempfile.TemporaryDirectory() as gov:
        Path(gov, "checks").mkdir()
        Path(gov, "checks", "stack-keys.json").write_text("[]")
        Path(gov, "index.json").write_text(json.dumps({"standards": list(index)}))
        proc = subprocess.run(
            [sys.executable, str(SELECT), "--governance-dir", gov, "--stacks", "", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    return {s["id"]: s for s in json.loads(proc.stdout)["selected"]}


class SelectorTests(unittest.TestCase):
    INDEX = (entry("SEC-PKG", "required"), entry("DEV-OPT", "advisory"), entry("SEC-SVC", "n/a"))

    def test_without_flag_tier_alone_decides(self):
        self.assertEqual(select("--tier", "T1", index=self.INDEX), {})

    def test_published_required_is_selected_as_required(self):
        got = select("--tier", "T1", "--published", index=self.INDEX)
        self.assertEqual(set(got), {"SEC-PKG"})
        self.assertEqual(got["SEC-PKG"]["applicability"], "required")
        self.assertEqual(got["SEC-PKG"]["matched_on"], "published package")

    def test_published_advisory_still_needs_a_trigger(self):
        got = select("--tier", "T1", "--published", "--brief-text", "dev-opt", index=self.INDEX)
        self.assertEqual(got["DEV-OPT"]["applicability"], "advisory")

    def test_effective_tier_is_what_rules_are_read_at(self):
        # /govern reads each rule's tier tags at effective_tier, so a T3-required rule
        # in an opted-in standard stays a hard rule for a published T1 package
        index = (*self.INDEX, entry("OPS-ALWAYS", "n/a", {t: "required" for t in TIERS_T3_UP}))
        got = select("--tier", "T1", "--published", "--brief-text", "dev-opt", index=index)
        self.assertEqual(
            {sid: e["effective_tier"] for sid, e in got.items()},
            {"SEC-PKG": "T3", "DEV-OPT": "T3", "OPS-ALWAYS": "T1"},
        )
        self.assertEqual(
            select("--tier", "T4", "--published", index=index)["SEC-PKG"]["effective_tier"], "T4"
        )
        self.assertEqual(select("--tier", "T1", index=index)["OPS-ALWAYS"]["effective_tier"], "T1")

    def test_published_never_weakens_tier_applicability(self):
        index = [entry("SEC-REQ", "advisory", {t: "required" for t in TIERS_T3_UP})]
        got = select("--tier", "T1", "--published", index=index)
        self.assertEqual(got["SEC-REQ"]["applicability"], "required")
        self.assertEqual(got["SEC-REQ"]["matched_on"], "required")


STANDARD = """---
id: {sid}
version: 1.0.0
published: {published}
verification:
  - cmd: "echo T1-check"
    expect: "exit 0"
    layer: G
    rules: [{sid}-01]
  - cmd: "echo T3-check"
    expect: "exit 0"
    layer: G
    rules: [{sid}-02]
    tiers: [T3, T4]
  - cmd: "echo T4-check"
    expect: "exit 0"
    layer: G
    rules: [{sid}-03]
    tiers: [T4]
---
"""


def ran_checks(tier: str, published_package, published: str = "required") -> dict:
    """Run the verifier over one fake standard; return {rule: True} for checks that ran."""
    with tempfile.TemporaryDirectory() as gov, tempfile.TemporaryDirectory() as proj:
        Path(gov, "standards", "security").mkdir(parents=True)
        Path(gov, "standards", "security", "sec-pkg.md").write_text(
            STANDARD.format(sid="SEC-PKG", published=published)
        )
        flag = "" if published_package is None else f"published_package: {published_package}\n"
        Path(proj, "GOVERNANCE.md").write_text(
            f"```yaml\ntier: {tier}\n{flag}standards:\n"
            "  - {id: SEC-PKG, version: 1.0.0}\nwaivers: []\n```\n"
        )
        proc = subprocess.run(
            [sys.executable, str(VERIFY), "--project", proj, "--governance-dir", gov, "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
    if not proc.stdout.strip():  # sys.exit(message): no report, exit 1
        return {"error": proc.stderr.strip()}
    return {r["id"]: True for r in json.loads(proc.stdout)["results"] if r["kind"] == "check"}


class VerifierTests(unittest.TestCase):
    def test_t1_not_published_runs_t1_checks_only(self):
        self.assertEqual(set(ran_checks("T1", None)), {"SEC-PKG-01"})

    def test_t1_published_runs_t3_scoped_checks(self):
        self.assertEqual(set(ran_checks("T1", "true")), {"SEC-PKG-01", "SEC-PKG-02"})

    def test_published_flag_false_changes_nothing(self):
        self.assertEqual(set(ran_checks("T1", "false")), {"SEC-PKG-01"})

    def test_standard_marked_na_is_not_uplifted(self):
        self.assertEqual(set(ran_checks("T1", "true", published="n/a")), {"SEC-PKG-01"})

    def test_t4_published_keeps_t4(self):
        self.assertEqual(set(ran_checks("T4", "true")), {"SEC-PKG-01", "SEC-PKG-02", "SEC-PKG-03"})

    def test_non_boolean_flag_is_rejected(self):
        self.assertIn("published_package", ran_checks("T1", '"yes"').get("error", ""))


class LintTests(unittest.TestCase):
    def test_required_on_the_four_families(self):
        for fam in ("SEC", "TST", "DEV", "LEG"):
            with self.subTest(fam=fam):
                self.assertTrue(lint.published_errors({"family": fam}, "x.md"))

    def test_optional_elsewhere(self):
        self.assertEqual(lint.published_errors({"family": "OPS"}, "x.md"), [])

    def test_values_are_validated(self):
        self.assertTrue(lint.published_errors({"family": "SEC", "published": "yes"}, "x.md"))
        self.assertTrue(lint.published_errors({"family": "OPS", "published": "yes"}, "x.md"))
        for value in ("required", "advisory", "n/a"):
            self.assertEqual(
                lint.published_errors({"family": "SEC", "published": value}, "x.md"), []
            )


class CorpusTests(unittest.TestCase):
    def test_standards_match_adr_0005_table(self):
        adr = (ROOT / "decisions" / "adr-0005-published-package-weight.md").read_text()
        table = {
            value: set(re.findall(r"[A-Z]+-[A-Z]+", ids))
            for value, ids in re.findall(
                r"^\| (required|advisory|n/a) \| (.+) \|$", adr, re.MULTILINE
            )
        }
        actual: dict[str, set[str]] = {"required": set(), "advisory": set(), "n/a": set()}
        for path in sorted((ROOT / "standards").rglob("*.md")):
            meta = yaml.safe_load(
                re.match(r"\A---\n(.*?)\n---\n", path.read_text(), re.DOTALL).group(1)
            )
            if meta["family"] in ("SEC", "TST", "DEV", "LEG"):
                actual[meta.get("published", "missing")].add(meta["id"])
        self.assertEqual(actual, table)


if __name__ == "__main__":
    unittest.main()
