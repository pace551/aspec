#!/usr/bin/env python3
"""Contract tests across /govern, /bootstrap-repo and DEV-CI's check.

#29's 🔴: /govern selected DEV-CI at T3 weight for a published T1 package, but
/bootstrap-repo's T1 rule said "no CI files", so the project failed DEV-CI. The skill
composes CI in prose, so these tests pin each piece of that chain:

- selection: select-standards.py picks DEV-CI at the tier bootstrap is told to build CI
  for (BUILD_TIER: T3/T4 at T3+, and for a published package at any tier)
- the skill: its T1 and T2 bullets defer to the published-package rule, which builds the
  T3 job set (T4 at T4)
- the templates: every scaffold stack has templates/ci/<stack>.yml (or a stated reason
  not to), and it passes dev-ci-present.sh at every tier bootstrap builds CI for
- the job lists: DEV-CI-01's table, dev-ci-present.sh and _fragments/ name the same jobs
"""

from __future__ import annotations

import functools
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELECT = ROOT / "checks" / "select-standards.py"
DEV_CI_PRESENT = ROOT / "checks" / "dev-ci-present.sh"
TEMPLATES = ROOT / "templates" / "ci"
TIERS = ("T1", "T2", "T3", "T4")


# The CI tier /bootstrap-repo builds for (tier, published), per its step 3; None: no CI.
BUILD_TIER = {
    ("T1", False): None, ("T2", False): None, ("T3", False): "T3", ("T4", False): "T4",
    ("T1", True): "T3", ("T2", True): "T3", ("T3", True): "T3", ("T4", True): "T4",
}  # fmt: skip
# Scaffold stacks without a CI template of their own, and why.
NO_CI_TEMPLATE = {
    "_common": "shared hooks and scripts, not a stack",
    "containers": "additive: rides on a language stack's CI (iac-scan fragment)",
    "data": "additive: data-store fragments merged into a language stack",
    "terraform": "additive: rides on a language stack's CI (iac-scan fragment)",
}


def stack_templates() -> dict[str, Path]:
    return {p.stem: p for p in sorted(TEMPLATES.glob("*.yml"))}


@functools.cache
def dev_ci_tier(tier: str, published: bool) -> str | None:
    """The effective tier DEV-CI is selected at (it's `stacks: all`), or None."""
    cmd = [sys.executable, str(SELECT), "--tier", tier, "--stacks", "python", "--brief-text", ""]
    out = subprocess.run(
        [*cmd, *(["--published"] if published else [])],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for entry in json.loads(out)["selected"]:
        if entry["id"] == "DEV-CI":
            return entry.get("effective_tier", tier)
    return None


def dev_ci_present(template: Path, tier: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        wf = Path(tmp, ".github", "workflows")
        wf.mkdir(parents=True)
        shutil.copy(template, wf / "ci.yml")
        return subprocess.run(
            ["bash", str(DEV_CI_PRESENT), "--tier", tier, "--project", tmp],
            capture_output=True,
            text=True,
            check=False,
        )


def standard_jobs() -> dict[str, list[str]]:
    """DEV-CI-01's job table: {"T3": [...], "T4": [...]}."""
    text = (ROOT / "standards" / "process" / "dev-ci.md").read_text()
    t3 = re.search(r"^\| T3 \| (.+?) — on", text, re.M).group(1)
    jobs = {"T3": re.findall(r"`([a-z-]+)`", t3)}
    t4 = re.search(r"^\| T4 \| T3 set \+ (.+?) \|", text, re.M).group(1)
    jobs["T4"] = jobs["T3"] + re.findall(r"`([a-z-]+)`", t4)
    return jobs


def script_jobs() -> dict[str, list[str]]:
    text = DEV_CI_PRESENT.read_text()
    return {
        tier: re.search(rf"^\s*{tier}\) required=\(([^)]*)\)", text, re.M).group(1).split()
        for tier in ("T3", "T4")
    }


class TierMatrixTests(unittest.TestCase):
    def test_selection_matches_what_bootstrap_builds(self):
        for (tier, published), build in BUILD_TIER.items():
            with self.subTest(tier=tier, published=published):
                selected = dev_ci_tier(tier, published)
                # DEV-CI below T3 is advisory/n-a: bootstrap builds no CI for it
                self.assertEqual(selected if selected in ("T3", "T4") else None, build)

    def test_every_scaffold_stack_has_a_ci_template(self):
        templates = stack_templates()
        for scaffold in sorted(p.name for p in (ROOT / "templates" / "scaffolds").iterdir()):
            if (ROOT / "templates" / "scaffolds" / scaffold).is_dir():
                with self.subTest(stack=scaffold):
                    self.assertTrue(scaffold in templates or scaffold in NO_CI_TEMPLATE)

    def test_template_passes_dev_ci_at_every_tier_bootstrap_builds(self):
        for stack, template in stack_templates().items():
            for tier in sorted({t for t in BUILD_TIER.values() if t}):
                with self.subTest(stack=stack, tier=tier):
                    proc = dev_ci_present(template, tier)
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class JobListAgreementTests(unittest.TestCase):
    def test_standard_and_script_name_the_same_jobs(self):
        self.assertEqual(standard_jobs(), script_jobs())

    def test_every_required_job_has_a_fragment(self):
        fragments = {p.stem for p in (TEMPLATES / "_fragments").glob("*.yml")}
        for job in standard_jobs()["T4"]:
            with self.subTest(job=job):
                self.assertIn(job, fragments)


class BootstrapProseTests(unittest.TestCase):
    def ci_bullets(self) -> dict[str, str]:
        skill = (ROOT / "skills" / "bootstrap-repo" / "SKILL.md").read_text(encoding="utf-8")
        section = skill.split("### 3. CI", 1)[1].split("\n### ", 1)[0]
        bullets = re.findall(r"^- \*\*(.+?)\*\*(.*?)(?=^- \*\*|\Z)", section, re.M | re.S)
        return {name: body for name, body in bullets}

    def test_t1_and_t2_defer_to_the_published_rule(self):
        bullets = self.ci_bullets()
        for tier in ("T1", "T2"):
            with self.subTest(tier=tier):
                self.assertRegex(bullets[tier], r"(?i)published\s+package")

    def test_published_rule_builds_the_t3_job_set(self):
        rule = next(b for name, b in self.ci_bullets().items() if name.startswith("Published"))
        self.assertRegex(rule, r"T3 job set")
        self.assertRegex(rule, r"T4 if the tier is T4")


if __name__ == "__main__":
    unittest.main()
