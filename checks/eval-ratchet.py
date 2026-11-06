#!/usr/bin/env python3
"""eval-ratchet.py — recorded LLM eval results must be fresh and must not regress
(AI-EVALS, ADR-0006). It never calls a model: running the suite is the project's job.

The project's runner writes a fresh evals/results.json on every run, without a hash:

  {"schema": 1, "model": "<model id>",
   "suites": {"<name>": {"kind": "capability" | "regression" | "safety",
                         "cases": <int>, "trials": <int>, "pass_rate": <0..1>}}}

`--stamp` adds "inputs_sha256": a hash of everything listed in the committed evals/inputs
file (one path per line; blank lines and `# comments` ignored). It refuses results that
are already stamped, so stale results can't be re-stamped without a rerun. The
algorithm, for runner authors who want to check it:

  entries = the lines of evals/inputs, each a literal path (no glob magic)
  files   = `git --literal-pathspecs ls-files -z -s --cached -- <entry>` for each entry,
            minus evals/results.json and .eval-baseline, sorted by path
  per file: path (UTF-8) + NUL + digest + LF, where digest is, for a regular file,
            the blob id `git hash-object --stdin-paths` gives its working-tree content
            (after the repo's eol and clean filters, so autocrlf and LFS clones agree);
            for a symlink, the hex sha256 of its target (also when core.symlinks=false
            checks it out as a file holding the target); for a submodule, its recorded
            commit id. A tracked file missing from the work tree is left out
  inputs_sha256 = hex sha256 of the concatenation

Only tracked files are hashed, so every clone computes the same hash. An untracked,
non-ignored file under an entry, an entry that matches no tracked file, and a prompts/
directory missing from the list are findings: commit, gitignore or fix them.

Modes (one at a time):
  --check (default)   read-only gate, run by /verify-compliance
  --stamp             validate fresh results.json and write inputs_sha256 into it
  --update-baseline   write .eval-baseline (each suite's kind, pass rate, cases and
                      runs = cases × trials) from fresh results. A drop within the noise band
                      keeps the old value. Lowering a suite beyond it, removing one,
                      shrinking its cases or runs, or relabelling a safety suite needs
                      --allow-lower and a waiver (C9)

The gate (--check) fails when, at every tier:
  results.json is missing, malformed, unstamped, or has fewer than 10 cases in total; a
  safety suite is below 1.0, relabelled, shrunk or missing against the baseline;
  .eval-baseline is malformed; a results file or the baseline is a symlink.
and at T2+ also when (at T1 these only warn, as AI-EVALS-03/05 are advisory there):
  the results are stale or untracked files sit under evals/inputs; a suite ran fewer than
  3 trials; .eval-baseline is missing; a baseline suite is missing from the results or
  ran fewer cases or times than its baseline; a suite is below its baseline by more than
  max(0.02, 2·sqrt(2·p(1−p)/n)), n = the baseline's runs, p = (baseline·n + 1)/(n + 2).

Usage: eval-ratchet.py [--project DIR] [--tier T1|T2|T3|T4]
                       [--check | --stamp | --update-baseline [--allow-lower]]
Exit 0 = pass, 1 = findings, 2 = usage error or an input it couldn't read (an
incomplete hash is never a pass).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
import tempfile
from pathlib import Path

RESULTS = "evals/results.json"
INPUTS = "evals/inputs"
BASELINE = ".eval-baseline"
NEVER_HASHED = {RESULTS, BASELINE}
KINDS = ("capability", "regression", "safety")
MIN_CASES = 10
MIN_TRIALS_STRICT = 3
BAND_FLOOR = 0.02
EPS = 1e-9
STRICT_TIERS = {"T2", "T3", "T4"}
GITLINK = "160000"
SYMLINK = "120000"
# git translates its warnings; the incomplete-scan check matches the English text
GIT_ENV = {**os.environ, "LC_ALL": "C", "LANGUAGE": "C"}


class Finding(Exception):
    """A problem in the project: exit 1."""


class Incomplete(Exception):
    """The gate couldn't read what it needs: exit 2."""


def noise_band(baseline: float, n: int) -> float:
    """How far below its baseline a suite of n runs (cases × trials) may score before it
    counts as a regression: a two-sample bound (the baseline is a noisy run too),
    smoothed so that a baseline of 1.0 still gets a band."""
    p = (baseline * n + 1) / (n + 2)
    return max(BAND_FLOOR, 2 * math.sqrt(2 * p * (1 - p) / n))


def is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def is_rate(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value <= 1


def guard(root: Path, rel: str) -> Path:
    """The path of a file this script reads or writes, refusing symlinks: a symlinked
    results file or baseline (or evals/ directory) could aim a write outside the
    project."""
    path = root / rel
    for p in (path.parent, path):
        if p != root and p.is_symlink():
            raise Finding(f"{p.relative_to(root)} is a symlink; it must be a regular file or dir")
    return path


def write_atomic(path: Path, text: str) -> None:
    """Write a temp file in the same directory and rename it into place: the final name
    is replaced, never followed."""
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    else:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        os.fchmod(fd, mode)  # mkstemp creates 0600; keep the file readable as before
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(path: Path, label: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Incomplete(f"{label}: {exc.strerror or exc}") from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise Finding(f"{label} is not valid JSON: {exc}") from exc


def load_results(root: Path) -> dict:
    path = guard(root, RESULTS)
    if not path.is_file():
        raise Finding(
            f"no {RESULTS}: run the project's evals, then eval-ratchet.py --stamp "
            "(AI-EVALS-01; a waiver covers an early prototype)"
        )
    data = read_json(path, RESULTS)
    problems = []
    if not isinstance(data, dict):
        raise Finding(f"{RESULTS} must be a JSON object")
    if data.get("schema") != 1 or isinstance(data.get("schema"), bool):
        problems.append(f'"schema" must be 1 (got {data.get("schema")!r})')
    if not isinstance(data.get("model"), str) or not data["model"].strip():
        problems.append('"model" must name the model id the suite ran against')
    suites = data.get("suites")
    if not isinstance(suites, dict) or not suites:
        problems.append('"suites" must be a non-empty object')
        suites = {}
    for name, s in suites.items():
        if not isinstance(s, dict):
            problems.append(f"suite {name!r} must be an object")
            continue
        if s.get("kind") not in KINDS:
            problems.append(f"suite {name!r}: kind must be one of {', '.join(KINDS)}")
        for key in ("cases", "trials"):
            if not is_count(s.get(key)):
                problems.append(f"suite {name!r}: {key} must be a whole number ≥ 1")
        if not is_rate(s.get("pass_rate")):
            problems.append(f"suite {name!r}: pass_rate must be a number from 0 to 1")
    if not problems:
        total = sum(s["cases"] for s in suites.values())
        if total < MIN_CASES:
            problems.append(f"the eval set needs at least {MIN_CASES} cases in total (has {total})")
    if problems:
        raise Finding(f"{RESULTS}: " + "; ".join(problems))
    return data


def read_inputs(root: Path) -> list[str]:
    path = root / INPUTS
    if not path.is_file():
        raise Finding(
            f"no {INPUTS}: list the prompt, model-config and tool-definition paths the "
            "results depend on, one per line"
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Incomplete(f"{INPUTS}: {exc.strerror or exc}") from exc
    entries = [s for line in text.splitlines() if (s := line.strip()) and not s.startswith("#")]
    if not entries:
        raise Finding(f"{INPUTS} lists no paths")
    if (root / "prompts").is_dir() and not any(
        e.removeprefix("./").rstrip("/") in ("prompts", ".", "") for e in entries
    ):
        raise Finding(f"{INPUTS} must list prompts/ (the directory exists)")
    return entries


def git_ls(root: Path, *args: str) -> list[str]:
    proc = subprocess.run(  # nosec B603 B607 - git ls-files, argv only, no shell
        ["git", "--literal-pathspecs", "ls-files", "-z", *args],
        cwd=root,
        capture_output=True,
        env=GIT_ENV,
        check=False,
    )
    # git only warns about an unreadable untracked directory and exits 0; other stderr
    # (trace output, config deprecation notices) doesn't mean files are missing
    if proc.returncode != 0 or b"could not open directory" in proc.stderr:
        raise Incomplete(f"git ls-files: {proc.stderr.decode(errors='replace').strip()}")
    return [f for f in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if f]


def tracked_entries(root: Path, entries: list[str]) -> dict[str, tuple[str, str]]:
    """path -> (mode, object id) for every tracked file under the entries. An entry that
    matches no tracked file is a finding: a typo would otherwise drop a dependency from
    the hash without a word."""
    files: dict[str, tuple[str, str]] = {}
    for entry in entries:
        lines = git_ls(root, "-s", "--cached", "--", entry)
        if not lines:
            raise Finding(
                f"{INPUTS}: {entry!r} matches no tracked file (commit it or fix the path)"
            )
        for line in lines:
            meta, _, path = line.partition("\t")
            mode, obj, _stage = meta.split(" ")
            files[path] = (mode, obj)
    for name in NEVER_HASHED:
        files.pop(name, None)
    if not files:
        raise Finding(f"{INPUTS} selects no files")
    return files


def untracked(root: Path, entries: list[str]) -> list[str]:
    found = git_ls(root, "--others", "--exclude-standard", "--", *entries)
    return sorted(set(found) - NEVER_HASHED)


def blob_ids(root: Path, paths: list[str]) -> list[str]:
    """The blob id git would store for each working-tree file, after the repo's eol
    conversion and clean filters (LFS included), so every clone of a commit agrees."""
    if not paths:
        return []
    if any("\n" in p for p in paths):
        raise Finding("an input path contains a newline; rename it")
    proc = subprocess.run(  # nosec B603 B607 - git hash-object, argv only, no shell
        ["git", "hash-object", "--stdin-paths"],
        cwd=root,
        input="".join(f"{p}\n" for p in paths).encode("utf-8", "surrogateescape"),
        capture_output=True,
        env=GIT_ENV,
        check=False,
    )
    ids = proc.stdout.decode().split()
    if proc.returncode != 0 or len(ids) != len(paths):
        raise Incomplete(f"git hash-object: {proc.stderr.decode(errors='replace').strip()}")
    return ids


def inputs_hash(root: Path, entries: list[str]) -> str:
    digests: dict[str, str] = {}
    blobs: list[str] = []
    for rel, (mode, obj) in sorted(tracked_entries(root, entries).items()):
        if mode == GITLINK:
            digests[rel] = obj  # a submodule: its recorded commit
            continue
        path = root / rel
        try:
            st = path.lstat()
            if stat.S_ISLNK(st.st_mode):
                digests[rel] = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
            elif mode == SYMLINK and stat.S_ISREG(st.st_mode):
                # a symlink checked out as a file holding its target (core.symlinks=false):
                # the same bytes, so the same digest as a real link
                digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif stat.S_ISREG(st.st_mode):
                blobs.append(rel)
            else:
                digests[rel] = "not-a-file"  # e.g. a directory where a file is tracked
        except FileNotFoundError:
            continue  # tracked but deleted: dropping it from the hash marks the change
        except OSError as exc:
            raise Incomplete(f"{rel}: {exc.strerror or exc}") from exc
    digests.update(zip(blobs, blob_ids(root, blobs), strict=True))
    h = hashlib.sha256()
    for rel in sorted(digests):
        h.update(rel.encode("utf-8", "surrogateescape") + b"\0" + digests[rel].encode() + b"\n")
    return h.hexdigest()


def load_baseline(root: Path) -> dict[str, dict] | None:
    path = guard(root, BASELINE)
    if not path.exists():
        return None
    data = read_json(path, BASELINE)
    suites = data.get("suites") if isinstance(data, dict) else None
    ok = (
        isinstance(data, dict)
        and data.get("schema") == 1
        and isinstance(suites, dict)
        and all(
            isinstance(v, dict)
            and v.get("kind") in KINDS
            and is_rate(v.get("pass_rate"))
            and is_count(v.get("cases"))
            and is_count(v.get("runs"))
            for v in suites.values()
        )
    )
    if not ok:
        raise Finding(
            f"{BASELINE} is malformed: expected "
            '{"schema": 1, "suites": {name: {"kind", "pass_rate", "cases", "runs"}}}. '
            "Restore it from git, or delete it and run --update-baseline (record a waiver "
            "for the lost values)"
        )
    return suites


def check(root: Path, tier: str) -> int:
    strict = tier in STRICT_TIERS
    data = load_results(root)
    entries = read_inputs(root)
    current = inputs_hash(root, entries)
    suites = data["suites"]
    fails: list[str] = []
    warns: list[str] = []
    notes: list[str] = []

    def problem(msg: str, always: bool = False) -> None:
        (fails if strict or always else warns).append(msg)

    stamp = data.get("inputs_sha256")
    if stamp is None:
        problem(f"{RESULTS} is not stamped: run eval-ratchet.py --stamp after the eval run", True)
    elif stamp != current:
        problem(
            f"results are stale: files in {INPUTS} changed since the last --stamp; "
            "rerun the evals, then --stamp"
        )
    if stray := untracked(root, entries):
        problem(
            f"untracked files under {INPUTS} entries ({', '.join(stray[:5])}"
            f"{', …' if len(stray) > 5 else ''}): commit or gitignore them"
        )
    for name, s in suites.items():
        if s["kind"] == "safety" and s["pass_rate"] < 1.0:
            problem(
                f"safety suite {name!r} at {s['pass_rate']:.3f}: one gated action in any "
                "trial is a finding, not noise (AI-EVALS-06)",
                True,
            )
        if s["trials"] < MIN_TRIALS_STRICT:
            problem(
                f"suite {name!r} ran {s['trials']} trial(s) per case; T2+ needs at least 3 trials"
            )

    baseline = load_baseline(root)
    if baseline is None:
        problem(f"no {BASELINE}: run eval-ratchet.py --update-baseline and commit it")
    else:
        for name, base in sorted(baseline.items()):
            s = suites.get(name)
            was_safety = base["kind"] == "safety"
            if s is None:
                problem(
                    f"suite {name!r} is in {BASELINE} but missing from {RESULTS}; removing "
                    "or renaming a suite needs --update-baseline --allow-lower and a waiver",
                    was_safety,
                )
            elif was_safety and s["kind"] != "safety":
                problem(
                    f"suite {name!r} was a safety suite and is now {s['kind']!r}; relabelling "
                    "needs --update-baseline --allow-lower and a waiver",
                    True,
                )
            elif (runs := s["cases"] * s["trials"]) < base["runs"] or s["cases"] < base["cases"]:
                problem(
                    f"suite {name!r} ran {s['cases']} cases / {runs} times, fewer than its "
                    f"baseline's {base['cases']} / {base['runs']}; shrinking a suite needs "
                    "--update-baseline --allow-lower and a waiver",
                    was_safety,
                )
            elif s["kind"] == "safety":
                continue  # held to 1.0 above; no noise band
            elif (
                s["pass_rate"]
                < base["pass_rate"] - (band := noise_band(base["pass_rate"], base["runs"])) - EPS
            ):
                problem(
                    f"suite {name!r} at {s['pass_rate']:.3f} is below its baseline "
                    f"{base['pass_rate']:.3f} by more than the noise band {band:.3f} "
                    f"(n={base['runs']})"
                )
        for name in sorted(set(suites) - set(baseline)):
            notes.append(f"suite {name!r} is not in {BASELINE} yet: --update-baseline after review")

    for msg in fails:
        print(f"eval-ratchet: FAIL — {msg}")
    for msg in warns:
        print(f"eval-ratchet: WARN — {msg} (advisory at {tier})")
    for msg in notes:
        print(f"eval-ratchet: note — {msg}")
    if fails:
        return 1
    print(f"eval-ratchet: OK ({len(suites)} suite(s), {tier})")
    return 0


def stamp(root: Path) -> int:
    data = load_results(root)
    if "inputs_sha256" in data:
        raise Finding(
            f"{RESULTS} is already stamped: rerun the evals (the runner writes a fresh, "
            "unstamped file), then --stamp"
        )
    entries = read_inputs(root)
    if stray := untracked(root, entries):
        raise Finding(
            f"untracked files under {INPUTS} entries ({', '.join(stray[:5])}): commit or "
            "gitignore them before stamping, so every clone computes the same hash"
        )
    data["inputs_sha256"] = inputs_hash(root, entries)
    write_atomic(root / RESULTS, json.dumps(data, indent=2) + "\n")
    print(f"eval-ratchet: stamped {RESULTS} ({data['inputs_sha256'][:12]}…)")
    return 0


def update_baseline(root: Path, allow_lower: bool) -> int:
    data = load_results(root)
    entries = read_inputs(root)
    if stray := untracked(root, entries):
        raise Finding(
            f"untracked files under {INPUTS} entries ({', '.join(stray[:5])}): commit or "
            "gitignore them before raising the baseline"
        )
    if data.get("inputs_sha256") != inputs_hash(root, entries):
        raise Finding(
            "results are stale or unstamped: rerun the evals and --stamp before --update-baseline"
        )
    suites = data["suites"]
    unsafe = [n for n, s in suites.items() if s["kind"] == "safety" and s["pass_rate"] < 1.0]
    if unsafe:
        raise Finding(f"safety suite(s) below 1.0 can't become the baseline: {', '.join(unsafe)}")
    old = load_baseline(root) or {}
    new: dict[str, dict] = {}
    lowered = []
    for name, s in sorted(suites.items()):
        rate, runs = float(s["pass_rate"]), s["cases"] * s["trials"]
        base = old.get(name)
        if base is not None:
            if base["kind"] == "safety" and s["kind"] != "safety":
                lowered.append(f"{name} (no longer a safety suite)")
            elif runs < base["runs"] or s["cases"] < base["cases"]:
                lowered.append(
                    f"{name} ({base['cases']}→{s['cases']} cases, {base['runs']}→{runs} runs)"
                )
            elif rate < base["pass_rate"]:
                if rate >= base["pass_rate"] - noise_band(base["pass_rate"], base["runs"]) - EPS:
                    rate = base["pass_rate"]  # within noise: keep the old bar
                else:
                    lowered.append(f"{name} {base['pass_rate']:.3f}→{rate:.3f}")
        new[name] = {"kind": s["kind"], "pass_rate": rate, "cases": s["cases"], "runs": runs}
    lowered += [f"{n} (removed)" for n in sorted(set(old) - set(new))]
    if lowered and not allow_lower:
        raise Finding(
            "this would lower "
            + ", ".join(lowered)
            + ": pass --allow-lower and record a waiver in GOVERNANCE.md (C9)"
        )
    write_atomic(
        guard(root, BASELINE),
        json.dumps({"schema": 1, "suites": new}, indent=2, sort_keys=True) + "\n",
    )
    if lowered:
        print(
            "eval-ratchet: WARN — lowered "
            + ", ".join(lowered)
            + "; record a waiver in GOVERNANCE.md (C9, as for TST-RATCHET-03)"
        )
    print(f"eval-ratchet: wrote {BASELINE} ({len(new)} suite(s)); commit it")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate recorded LLM eval results (AI-EVALS).")
    ap.add_argument("--project", default=".", type=Path)
    ap.add_argument("--tier", choices=["T1", "T2", "T3", "T4"], default="T2")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only gate (default)")
    mode.add_argument("--stamp", action="store_true", help="write inputs_sha256 into results")
    mode.add_argument("--update-baseline", action="store_true", help="write .eval-baseline")
    ap.add_argument("--allow-lower", action="store_true", help="with --update-baseline")
    args = ap.parse_args()
    if args.allow_lower and not args.update_baseline:
        ap.error("--allow-lower only applies to --update-baseline")
    root = args.project.resolve()
    try:
        if args.stamp:
            return stamp(root)
        if args.update_baseline:
            return update_baseline(root, args.allow_lower)
        return check(root, args.tier)
    except Finding as exc:
        print(f"eval-ratchet: FAIL — {exc}")
        return 1
    except Incomplete as exc:
        print(f"eval-ratchet: incomplete — {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
