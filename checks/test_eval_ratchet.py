#!/usr/bin/env python3
"""Tests for eval-ratchet.py (ADR-0006) and the AI-EVALS verification cmds that run it."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml
from hostile_tree import HOSTILE_DIR, Tree, can_lock, clean_env, tree

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "checks" / "eval-ratchet.py"
_fm = re.match(
    r"\A---\n(.*?)\n---\n",
    (ROOT / "standards" / "ai" / "ai-evals.md").read_text(),
    re.DOTALL,
)
GATE_CMDS = {
    tuple(v.get("tiers") or ("T1", "T2", "T3", "T4")): str(v["cmd"])
    for v in yaml.safe_load(_fm.group(1))["verification"]
    if "eval-ratchet.py" in str(v["cmd"])
}

PROMPT = "You are a triage agent.\n"
INPUTS = "prompts/\nevals/cases/\n"


def suite(kind: str = "regression", cases: int = 20, trials: int = 3, rate: float = 1.0):
    return {"kind": kind, "cases": cases, "trials": trials, "pass_rate": rate}


def results(**suites: dict) -> str:
    return json.dumps({"schema": 1, "model": "model-x-20260101", "suites": suites})


DEFAULT_SUITES = {
    "triage": suite(),
    "injection": suite("safety", cases=10, trials=3, rate=1.0),
}


def project(t: Tree, suites: dict | None = None, **extra: str) -> Tree:
    """A committed LLM project with prompts, cases, an inputs list and unstamped results."""
    files = {
        "prompts/system.md": PROMPT,
        "evals/cases/triage.jsonl": '{"input": "x", "expected": "urgent"}\n',
        "evals/inputs": INPUTS,
        "evals/results.json": results(**(suites or DEFAULT_SUITES)),
        **extra,
    }
    return t.write(files).commit()


def run(t: Tree, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=t.root,
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )


def ready(t: Tree, suites: dict | None = None, **extra: str) -> Tree:
    """project() + stamped results + a baseline taken from them."""
    project(t, suites, **extra)
    for mode in ("--stamp", "--update-baseline"):
        proc = run(t, mode)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    return t


def set_rate(t: Tree, name: str, rate: float, **changes) -> None:
    """Rewrite one suite's result, keeping the stamp (the inputs didn't change)."""
    path = t.root / "evals" / "results.json"
    data = json.loads(path.read_text())
    data["suites"][name] = {**data["suites"][name], "pass_rate": rate, **changes}
    path.write_text(json.dumps(data))


def baseline(t: Tree) -> dict:
    return json.loads((t.root / ".eval-baseline").read_text())["suites"]


def reference_hash(t: Tree, inputs: list[str]) -> str:
    """The ADR-0006 hash, computed independently of eval-ratchet.py: what a runner
    author can rely on."""
    out = subprocess.run(
        ["git", "--literal-pathspecs", "ls-files", "-z", "-s", "--cached", "--", *inputs],
        cwd=t.root,
        capture_output=True,
        check=True,
        env=clean_env(),
    ).stdout.decode()
    files = {}
    for line in filter(None, out.split("\0")):
        meta, _, path = line.partition("\t")
        files[path] = meta.split(" ")[:2]
    h = hashlib.sha256()
    for path in sorted(set(files) - {"evals/results.json", ".eval-baseline"}):
        mode, obj = files[path]
        p = t.root / path
        if mode == "160000":
            digest = obj
        elif mode == "120000":
            digest = hashlib.sha256(os.fsencode(os.readlink(p))).hexdigest()
        else:  # the blob id git computes for the working-tree file
            digest = t.git("hash-object", "--", path).strip()
        h.update(path.encode() + b"\0" + digest.encode() + b"\n")
    return h.hexdigest()


def rerun(t: Tree) -> None:
    """What the project's runner does: write a fresh, unstamped results.json."""
    path = t.root / "evals" / "results.json"
    data = json.loads(path.read_text())
    data.pop("inputs_sha256", None)
    path.write_text(json.dumps(data))


class HashContractTests(unittest.TestCase):
    def test_stamp_matches_the_documented_algorithm(self):
        with tree() as t:
            project(t)
            self.assertEqual(run(t, "--stamp").returncode, 0)
            stamped = json.loads((t.root / "evals/results.json").read_text())
            self.assertEqual(
                stamped["inputs_sha256"], reference_hash(t, ["prompts/", "evals/cases/"])
            )
            self.assertEqual(stamped["model"], "model-x-20260101")  # other keys kept

    def test_results_and_baseline_never_feed_the_hash(self):
        with tree() as t:
            ready(t)
            (t.root / "evals/inputs").write_text("prompts/\nevals/\n.eval-baseline\n")
            t.commit()
            rerun(t)
            self.assertEqual(run(t, "--stamp").returncode, 0)
            set_rate(t, "triage", 1.0)  # rewrite results.json after stamping
            self.assertEqual(run(t, "--update-baseline").returncode, 0)
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_hostile_paths_hash_and_go_stale(self):
        with tree() as t:
            ready(t, **{f"prompts/{HOSTILE_DIR}/tool.md": "tool\n"})
            (t.root / "prompts" / HOSTILE_DIR / "tool.md").write_text("changed\n")
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("stale", proc.stdout)

    def test_symlink_target_change_goes_stale(self):
        with tree() as t:
            project(t)
            (t.root / "prompts" / "link.md").symlink_to("system.md")
            t.commit()
            run(t, "--stamp")
            run(t, "--update-baseline")
            (t.root / "prompts" / "link.md").unlink()
            (t.root / "prompts" / "link.md").symlink_to("other.md")
            self.assertEqual(run(t, "--check").returncode, 1)


class FreshnessTests(unittest.TestCase):
    def test_fresh_results_pass(self):
        with tree() as t:
            ready(t)
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("OK", proc.stdout)

    def test_edited_prompt_is_stale(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/system.md").write_text(PROMPT + "Be terse.\n")
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("stale", proc.stdout)

    def test_new_untracked_prompt_is_stale(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/new.md").write_text("new\n")
            self.assertEqual(run(t, "--check").returncode, 1)

    def test_deleted_prompt_is_stale(self):
        with tree() as t:
            ready(t, **{"prompts/extra.md": "x\n"})
            (t.root / "prompts/extra.md").unlink()
            self.assertEqual(run(t, "--check").returncode, 1)

    def test_unstamped_results_fail(self):
        with tree() as t:
            project(t)
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("--stamp", proc.stdout)

    def test_stale_is_only_a_warning_at_t1(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/system.md").write_text("changed\n")
            proc = run(t, "--check", "--tier", "T1")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("WARN", proc.stdout)


class InputsTests(unittest.TestCase):
    def test_missing_results_fail(self):
        with tree() as t:
            project(t)
            (t.root / "evals/results.json").unlink()
            for tier in ("T1", "T2"):
                proc = run(t, "--check", "--tier", tier)
                self.assertEqual(proc.returncode, 1, tier)
                self.assertIn("results.json", proc.stdout)

    def test_missing_inputs_list_fails(self):
        with tree() as t:
            project(t)
            (t.root / "evals/inputs").unlink()
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("evals/inputs", proc.stdout)

    def test_inputs_must_cover_prompts(self):
        with tree() as t:
            project(t, **{"evals/inputs": "evals/cases/\n"})
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("prompts/", proc.stdout)

    def test_inputs_comments_blank_lines_and_dot_slash(self):
        with tree() as t:
            ready(t, **{"evals/inputs": "# what the evals depend on\n\n./prompts\nevals/cases\n"})
            self.assertEqual(run(t, "--check").returncode, 0)

    def test_empty_inputs_selection_fails(self):
        with tree() as t:
            project(t, **{"evals/inputs": "nothing-here/\n"})
            (t.root / "prompts/system.md").unlink()
            (t.root / "prompts").rmdir()
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("matches no tracked file", proc.stdout)

    @unittest.skipUnless(can_lock(), "chmod 000 stops nobody when running as root")
    def test_unreadable_input_is_incomplete(self):
        with tree() as t:
            ready(t)
            with t.locked("prompts/system.md"):
                proc = run(t, "--check")
            self.assertEqual(proc.returncode, 2, proc.stdout)

    def test_not_a_git_repo_is_a_usage_error(self):
        with tree() as t:
            t.write({"evals/inputs": INPUTS, "evals/results.json": results(**DEFAULT_SUITES)})
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 2, proc.stdout)


class SchemaTests(unittest.TestCase):
    def check_bad(self, raw: str, needle: str) -> None:
        with tree() as t:
            project(t, **{"evals/results.json": raw})
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn(needle, proc.stdout)

    def test_malformed_json(self):
        self.check_bad("{not json", "not valid JSON")

    def test_wrong_schema_version(self):
        self.check_bad(json.dumps({"schema": 2, "model": "m", "suites": {"a": suite()}}), "schema")

    def test_missing_model(self):
        self.check_bad(json.dumps({"schema": 1, "suites": {"a": suite()}}), "model")

    def test_no_suites(self):
        self.check_bad(json.dumps({"schema": 1, "model": "m", "suites": {}}), "suites")

    def test_unknown_kind(self):
        self.check_bad(results(a=suite(kind="vibes")), "kind")

    def test_pass_rate_out_of_range(self):
        self.check_bad(results(a=suite(rate=1.5)), "pass_rate")

    def test_bool_is_not_a_count(self):
        self.check_bad(results(a={**suite(), "trials": True}), "trials")

    def test_too_few_cases(self):
        self.check_bad(results(a=suite(cases=4), b=suite(cases=5)), "at least 10")


class EdgeCaseTests(unittest.TestCase):
    def test_results_must_be_an_object(self):
        with tree() as t:
            project(t, **{"evals/results.json": "[]"})
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("JSON object", proc.stdout)

    def test_suite_must_be_an_object(self):
        with tree() as t:
            project(t, **{"evals/results.json": results(a=[1, 2])})
            self.assertEqual(run(t, "--stamp").returncode, 1)

    def test_inputs_with_only_comments_fail(self):
        with tree() as t:
            project(t, **{"evals/inputs": "# nothing yet\n\n"})
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("lists no paths", proc.stdout)

    def test_submodule_hashes_its_commit(self):
        with tree() as t:
            project(t)
            t.nested_repo("prompts/vendored").commit()
            self.assertEqual(run(t, "--stamp").returncode, 0)
            self.assertEqual(run(t, "--update-baseline").returncode, 0)
            self.assertEqual(run(t, "--check").returncode, 0)
            sub = Tree(t.root / "prompts" / "vendored")
            sub.write({"README": "bumped\n"}).commit()
            t.git("add", "prompts/vendored")
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("stale", proc.stdout)

    def test_allow_lower_without_update_is_a_usage_error(self):
        with tree() as t:
            ready(t)
            self.assertEqual(run(t, "--check", "--allow-lower").returncode, 2)

    @unittest.skipUnless(can_lock(), "chmod 000 stops nobody when running as root")
    def test_unreadable_results_are_incomplete(self):
        with tree() as t:
            ready(t)
            with t.locked("evals/results.json"):
                self.assertEqual(run(t, "--check").returncode, 2)

    @unittest.skipUnless(can_lock(), "chmod 000 stops nobody when running as root")
    def test_unreadable_inputs_list_is_incomplete(self):
        with tree() as t:
            ready(t)
            with t.locked("evals/inputs"):
                self.assertEqual(run(t, "--check").returncode, 2)


class GateTests(unittest.TestCase):
    def test_safety_below_one_fails_at_every_tier(self):
        with tree() as t:
            ready(t)
            set_rate(t, "injection", 29 / 30)
            for tier in ("T1", "T2", "T4"):
                proc = run(t, "--check", "--tier", tier)
                self.assertEqual(proc.returncode, 1, tier)
                self.assertIn("safety", proc.stdout)

    def test_noise_band_matches_adr_examples(self):
        # 20 x 3 at a 1.0 baseline passes at 58/60 and fails at 57/60
        with tree() as t:
            ready(t)
            set_rate(t, "triage", 58 / 60)
            self.assertEqual(run(t, "--check").returncode, 0)
            set_rate(t, "triage", 57 / 60)
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("triage", proc.stdout)

    def test_small_suite_band(self):
        # 10 x 1 at a 0.9 baseline: 6/10 is within the band, 5/10 is not. At T1 the
        # regression gate is advisory, so the drop warns rather than fails.
        suites = {"triage": suite(cases=10, trials=1, rate=0.9)}
        with tree() as t:
            ready(t, suites)
            set_rate(t, "triage", 0.6)
            proc = run(t, "--check", "--tier", "T1")
            self.assertEqual(proc.returncode, 0)
            self.assertNotIn("below its baseline", proc.stdout)
            set_rate(t, "triage", 0.5)
            proc = run(t, "--check", "--tier", "T1")
            self.assertEqual(proc.returncode, 0)
            self.assertIn("WARN", proc.stdout)
            self.assertIn("below its baseline", proc.stdout)

    def test_within_band_update_keeps_the_old_bar(self):
        with tree() as t:
            ready(t)
            set_rate(t, "triage", 59 / 60)
            proc = run(t, "--update-baseline")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertEqual(baseline(t)["triage"]["pass_rate"], 1.0)

    def test_band_formula(self):
        spec = importlib.util.spec_from_file_location("eval_ratchet", GATE)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        self.assertAlmostEqual(gate.noise_band(1.0, 60), 0.0457, places=3)
        self.assertAlmostEqual(gate.noise_band(0.9, 10), 1 / 3, places=3)
        self.assertEqual(gate.noise_band(1.0, 100000), 0.02)  # the floor
        p = (0.5 * 50 + 1) / 52
        self.assertAlmostEqual(gate.noise_band(0.5, 50), 2 * math.sqrt(2 * p * (1 - p) / 50))

    def test_missing_suite_fails(self):
        with tree() as t:
            ready(t)
            path = t.root / "evals/results.json"
            data = json.loads(path.read_text())
            data["suites"]["triage_v2"] = data["suites"].pop("triage")
            path.write_text(json.dumps(data))
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("triage", proc.stdout)

    def test_new_suite_passes_with_a_note(self):
        with tree() as t:
            ready(t)
            set_rate(t, "triage", 1.0)
            path = t.root / "evals/results.json"
            data = json.loads(path.read_text())
            data["suites"]["extraction"] = suite("capability", rate=0.3)
            path.write_text(json.dumps(data))
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("extraction", proc.stdout)

    def test_trials_floor_by_tier(self):
        suites = {"triage": suite(cases=12, trials=1)}
        with tree() as t:
            ready(t, suites)
            self.assertEqual(run(t, "--check", "--tier", "T1").returncode, 0)
            for tier in ("T2", "T3", "T4"):
                proc = run(t, "--check", "--tier", tier)
                self.assertEqual(proc.returncode, 1, tier)
                self.assertIn("trials", proc.stdout)

    def test_missing_baseline(self):
        with tree() as t:
            project(t)
            run(t, "--stamp")
            self.assertEqual(run(t, "--check", "--tier", "T1").returncode, 0)
            proc = run(t, "--check", "--tier", "T2")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("--update-baseline", proc.stdout)

    def test_malformed_baseline_fails(self):
        with tree() as t:
            ready(t)
            (t.root / ".eval-baseline").write_text("0.9\n")
            self.assertEqual(run(t, "--check", "--tier", "T1").returncode, 1)

    def test_check_writes_nothing(self):
        with tree() as t:
            project(t)
            before = (t.root / "evals/results.json").read_bytes()
            run(t, "--check")
            run(t)  # no mode flag: the read-only check as well
            self.assertEqual((t.root / "evals/results.json").read_bytes(), before)
            self.assertFalse((t.root / ".eval-baseline").exists())


class ReviewFindingTests(unittest.TestCase):
    """Holes found in review: each must stay closed."""

    def test_restamping_stale_results_is_refused(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/system.md").write_text("changed\n")
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("already stamped", proc.stdout)
            self.assertEqual(run(t, "--check").returncode, 1)  # still stale

    def test_shrinking_a_suite_fails(self):
        suites = {"triage": suite(cases=10, trials=3, rate=0.9), "other": suite(cases=10)}
        with tree() as t:
            ready(t, suites)
            set_rate(t, "triage", 0.34, cases=1)
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("fewer than its baseline", proc.stdout)
            self.assertEqual(run(t, "--update-baseline").returncode, 1)  # needs --allow-lower

    def test_relabelling_a_safety_suite_fails_at_every_tier(self):
        with tree() as t:
            ready(t)
            set_rate(t, "injection", 0.95, kind="capability")
            for tier in ("T1", "T2"):
                proc = run(t, "--check", "--tier", tier)
                self.assertEqual(proc.returncode, 1, tier)
                self.assertIn("was a safety suite", proc.stdout)
            self.assertEqual(run(t, "--update-baseline").returncode, 1)

    def test_untracked_input_files(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/.DS_Store").write_text("x")
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("untracked", proc.stdout)
            self.assertIn("prompts/.DS_Store", proc.stdout)
            proc = run(t, "--check", "--tier", "T1")
            self.assertEqual(proc.returncode, 0)
            self.assertIn("WARN", proc.stdout)
            (t.root / ".gitignore").write_text(".DS_Store\n")
            self.assertEqual(run(t, "--check").returncode, 0)

    def test_untracked_input_files_block_stamping(self):
        with tree() as t:
            project(t)
            (t.root / "prompts/draft.md").write_text("draft\n")
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("prompts/draft.md", proc.stdout)

    def test_typo_in_inputs_fails(self):
        with tree() as t:
            project(t, **{"evals/inputs": "prompts/\nconfig/model.tml\n", "config/model.toml": "m"})
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("config/model.tml", proc.stdout)

    def test_git_stderr_noise_is_not_incomplete(self):
        with tree() as t:
            ready(t)
            proc = subprocess.run(
                [sys.executable, str(GATE), "--check"],
                cwd=t.root,
                capture_output=True,
                text=True,
                env=clean_env(GIT_TRACE="1"),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_inputs_naming_only_excluded_files_fail(self):
        with tree() as t:
            project(t, **{"evals/inputs": "evals/results.json\n"})
            (t.root / "prompts/system.md").unlink()
            (t.root / "prompts").rmdir()
            t.commit()
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("selects no files", proc.stdout)

    def test_malformed_baseline_says_how_to_recover(self):
        with tree() as t:
            ready(t)
            (t.root / ".eval-baseline").write_text('{"schema": 2}')
            proc = run(t, "--check")
            self.assertIn("delete it", proc.stdout)


class DeltaReviewTests(unittest.TestCase):
    """Holes found reviewing the first round of fixes."""

    def test_shrinking_a_safety_suite_fails_at_every_tier(self):
        with tree() as t:
            ready(t, {"triage": suite(cases=20), "injection": suite("safety", cases=10)})
            set_rate(t, "injection", 1.0, cases=1, trials=1)
            for tier in ("T1", "T2"):
                proc = run(t, "--check", "--tier", tier)
                self.assertEqual(proc.returncode, 1, tier)
                self.assertIn("fewer than its", proc.stdout)

    def test_fewer_cases_with_more_trials_fails(self):
        with tree() as t:
            ready(t, {"triage": suite(cases=20, rate=0.95), "other": suite(cases=10)})
            set_rate(t, "triage", 1.0, cases=1, trials=60)  # same runs, 1 case
            self.assertEqual(run(t, "--check").returncode, 1)
            self.assertEqual(run(t, "--update-baseline").returncode, 1)

    def test_renaming_a_safety_suite_fails_at_t1(self):
        with tree() as t:
            ready(t)
            path = t.root / "evals/results.json"
            data = json.loads(path.read_text())
            data["suites"]["injection_v2"] = {
                **data["suites"].pop("injection"),
                "kind": "capability",
            }
            path.write_text(json.dumps(data))
            proc = run(t, "--check", "--tier", "T1")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("missing", proc.stdout)

    def test_crlf_checkout_hashes_like_the_lf_one(self):
        # a Windows clone (core.autocrlf=true) has CRLF bytes for the same commit
        with tree() as t:
            ready(t)
            t.git("config", "core.autocrlf", "true")
            (t.root / "prompts/system.md").write_bytes(PROMPT.replace("\n", "\r\n").encode())
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_symlink_checked_out_as_a_file_hashes_like_the_link(self):
        # core.symlinks=false checks a link out as a file holding its target
        with tree() as t:
            project(t)
            (t.root / "prompts/link.md").symlink_to("system.md")
            t.commit()
            run(t, "--stamp")
            run(t, "--update-baseline")
            (t.root / "prompts/link.md").unlink()
            (t.root / "prompts/link.md").write_text("system.md")
            proc = run(t, "--check")
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_written_files_keep_a_readable_mode(self):
        with tree() as t:
            ready(t)
            umask = os.umask(0)
            os.umask(umask)
            for rel in ("evals/results.json", ".eval-baseline"):
                mode = (t.root / rel).stat().st_mode & 0o777
                self.assertEqual(mode, 0o666 & ~umask, rel)

    def test_update_baseline_refuses_untracked_inputs(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/draft.md").write_text("draft\n")
            proc = run(t, "--update-baseline")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("prompts/draft.md", proc.stdout)


class HashEdgeTests(unittest.TestCase):
    def test_inputs_with_only_a_submodule(self):
        with tree() as t:
            project(t, **{"evals/inputs": "vendored\n"})
            (t.root / "prompts/system.md").unlink()
            (t.root / "prompts").rmdir()
            t.nested_repo("vendored").commit()
            self.assertEqual(run(t, "--stamp").returncode, 0)

    def test_newline_in_an_input_path_fails(self):
        with tree() as t:
            project(t, **{"prompts/a\nb.md": "x\n"})
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("newline", proc.stdout)

    def test_directory_where_a_file_is_tracked_is_stale(self):
        with tree() as t:
            ready(t, **{"prompts/extra.md": "x\n"})
            (t.root / "prompts/extra.md").unlink()
            (t.root / "prompts/extra.md").mkdir()
            self.assertEqual(run(t, "--check").returncode, 1)

    @unittest.skipUnless(can_lock(), "chmod 000 stops nobody when running as root")
    def test_unreadable_input_directory_is_incomplete(self):
        with tree() as t:
            ready(t, **{"prompts/sub/deep.md": "x\n"})
            with t.locked("prompts/sub"):
                proc = run(t, "--check")
            self.assertEqual(proc.returncode, 2, proc.stdout)


class SymlinkTests(unittest.TestCase):
    """A repo must not be able to aim the gate's writes outside itself."""

    def test_dangling_baseline_symlink_is_never_written_through(self):
        with tree() as t:
            project(t)
            self.assertEqual(run(t, "--stamp").returncode, 0)
            target = t.root.parent / "outside-target"
            (t.root / ".eval-baseline").symlink_to(target)
            proc = run(t, "--update-baseline")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("symlink", proc.stdout)
            self.assertFalse(target.exists())
            self.assertEqual(run(t, "--check").returncode, 1)

    def test_results_symlink_is_refused(self):
        with tree() as t:
            project(t)
            real = t.root / "evals" / "real.json"
            (t.root / "evals/results.json").rename(real)
            (t.root / "evals/results.json").symlink_to("real.json")
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("symlink", proc.stdout)

    def test_evals_dir_symlink_is_refused(self):
        with tree() as t:
            project(t)
            (t.root / "evals").rename(t.root / "evals-real")
            (t.root / "evals").symlink_to("evals-real")
            proc = run(t, "--stamp")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("symlink", proc.stdout)

    def test_writes_leave_no_temp_files(self):
        with tree() as t:
            ready(t)
            leftovers = [p.name for p in t.root.rglob("*.tmp")]
            self.assertEqual(leftovers, [])


class UpdateBaselineTests(unittest.TestCase):
    def test_writes_every_suite(self):
        with tree() as t:
            ready(t)
            baseline = json.loads((t.root / ".eval-baseline").read_text())
            self.assertEqual(
                baseline,
                {
                    "schema": 1,
                    "suites": {
                        "triage": {
                            "kind": "regression",
                            "pass_rate": 1.0,
                            "cases": 20,
                            "runs": 60,
                        },
                        "injection": {"kind": "safety", "pass_rate": 1.0, "cases": 10, "runs": 30},
                    },
                },
            )

    def test_refuses_stale_results(self):
        with tree() as t:
            ready(t)
            (t.root / "prompts/system.md").write_text("changed\n")
            proc = run(t, "--update-baseline")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("stale", proc.stdout)

    def test_lowering_needs_allow_lower(self):
        with tree() as t:
            ready(t)
            set_rate(t, "triage", 0.5)
            proc = run(t, "--update-baseline")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("--allow-lower", proc.stdout)
            self.assertEqual(baseline(t)["triage"]["pass_rate"], 1.0)
            proc = run(t, "--update-baseline", "--allow-lower")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("waiver", proc.stdout)
            self.assertEqual(baseline(t)["triage"]["pass_rate"], 0.5)

    def test_removing_a_suite_needs_allow_lower(self):
        with tree() as t:
            ready(t)
            path = t.root / "evals/results.json"
            data = json.loads(path.read_text())
            del data["suites"]["triage"]
            data["suites"]["injection"]["cases"] = 12
            path.write_text(json.dumps(data))
            self.assertEqual(run(t, "--update-baseline").returncode, 1)
            self.assertEqual(run(t, "--update-baseline", "--allow-lower").returncode, 0)

    def test_safety_below_one_cannot_become_the_baseline(self):
        with tree() as t:
            ready(t)
            set_rate(t, "injection", 0.9)
            self.assertEqual(run(t, "--update-baseline", "--allow-lower").returncode, 1)


class VerificationCmdTests(unittest.TestCase):
    """The AI-EVALS cmds, run the way run-verification.py runs them."""

    def run_cmd(self, t: Tree, tiers: tuple[str, ...], gov: Path = ROOT) -> int:
        return subprocess.run(
            ["bash", "-c", GATE_CMDS[tiers]],
            cwd=t.root,
            env=clean_env(GOVERNANCE_DIR=str(gov)),
            capture_output=True,
            check=False,
        ).returncode

    def test_one_cmd_per_tier_band(self):
        self.assertEqual(sorted(GATE_CMDS), [("T1",), ("T2", "T3", "T4")])

    def test_ready_project_passes_both(self):
        with tree() as t:
            ready(t)
            for tiers in GATE_CMDS:
                self.assertEqual(self.run_cmd(t, tiers), 0, tiers)

    def test_t1_cmd_tolerates_single_trials_t2_does_not(self):
        with tree() as t:
            ready(t, {"triage": suite(cases=12, trials=1)})
            self.assertEqual(self.run_cmd(t, ("T1",)), 0)
            self.assertNotEqual(self.run_cmd(t, ("T2", "T3", "T4")), 0)

    def test_missing_results_fail_both(self):
        with tree() as t:
            project(t)
            (t.root / "evals/results.json").unlink()
            for tiers in GATE_CMDS:
                self.assertNotEqual(self.run_cmd(t, tiers), 0, tiers)

    def test_missing_script_fails(self):
        with tree() as t, tree() as gov:
            ready(t)
            for tiers in GATE_CMDS:
                self.assertNotEqual(self.run_cmd(t, tiers, gov.root), 0, tiers)


if __name__ == "__main__":
    unittest.main()
