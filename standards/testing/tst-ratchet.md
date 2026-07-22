---
id: TST-RATCHET
title: Coverage Ratchet
family: TST
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - coverage
  - ratchet
  - baseline
  - coverage-baseline
  - pytest-cov
  - istanbul
  - lcov
  - coverage.json
requires: []
verification:
  - cmd: "sh -c 'python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py --check; rc=$?; [ $rc -eq 0 ] || [ $rc -eq 2 ]'"
    expect: "exit 0 — coverage ≥ baseline − tolerance (exit 2 'no coverage data yet' tolerated on fresh scaffolds; the stack gate produces the data)"
    layer: G
    rules: [TST-RATCHET-01, TST-RATCHET-02]
    tiers: [T2, T3, T4]
  - cmd: "sh -c '[ ! -f .coverage-baseline ] || git ls-files --error-unmatch .coverage-baseline >/dev/null 2>&1'"
    expect: "exit 0 — .coverage-baseline, when present, is committed at the repo root"
    layer: G
    rules: [TST-RATCHET-01]
  - cmd: "attest: the baseline has never been reset or lowered without a waiver in GOVERNANCE.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-RATCHET-03]
    tiers: [T2, T3, T4]
  - cmd: "attest: the test run emits coverage in a ratchet-readable format and stale coverage artifacts from other formats are cleaned"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-RATCHET-04]
    tiers: [T2, T3, T4]
last_review: 2026-07-22
---

# Coverage Ratchet (TST-RATCHET)

## Abstract

Mechanics of Constitution C3's "coverage never decreases", implemented by
`checks/coverage-ratchet.py`. A `.coverage-baseline` file committed at the repo root
records the honest current coverage; every subsequent run must meet it, and improvements
raise it automatically. No fixed percentage is ever set (`TST-POLICY-05`) — the ratchet
compares the project against its own past, which is the only comparison that can't be
gamed by picking a flattering number. Required at T2+ (wrong analysis and user-facing code
both deserve a floor); advisory at T1. Verification runs the ratchet read-only
(`--check`); lowering the baseline requires a waiver.

## Normative Rules

### TST-RATCHET-01 — `.coverage-baseline` MUST be committed at the repo root and only ever move up

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

The baseline is a single number (e.g. `84.10`) written by the first ratchet run and
committed like source. On every run, current coverage below `baseline − tolerance` fails
(exit 1); coverage above the baseline raises the file to the new value, and that raise is
committed with the change that earned it. The default tolerance of 0.1 percentage points
absorbs float noise (a line-count change shifting 87.43% → 87.39% is not a regression) —
it is noise headroom, never a budget to spend deliberately. The baseline is per-repo, at
the root, exactly where `coverage-ratchet.py` looks.

### TST-RATCHET-02 — Verification MUST invoke the ratchet in `--check` mode

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`--check` is read-only: it never writes or initializes the baseline, so a
`/verify-compliance` run leaves the working tree untouched (verification never mutates —
authoring invariant, and it keeps CI runs from producing uncommittable baseline bumps).
Baseline raises happen in normal development runs (no flag), where the resulting file
change is reviewed and committed deliberately. In `--check` mode a missing baseline
passes with a notice — initialization is a development act, not a verification side
effect.

### TST-RATCHET-03 — Resetting or lowering the baseline MUST have a waiver

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The only legitimate reasons the number goes down: deleting well-tested code whose absence
drops the aggregate, or excluding generated/vendored files that were inflating it. Both
get a waiver in `GOVERNANCE.md` — `{rule_id: TST-RATCHET-03, reason, expires}` — and the
new baseline is set from a fresh honest run, in its own commit, with the waiver cited in
the commit message. Editing the file to make a red gate green without a waiver is silent
drift, the one unforgivable failure mode (C9).

### TST-RATCHET-04 — The test run MUST emit coverage in a ratchet-readable format

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

`coverage-ratchet.py` reads, first match wins: an explicit `--value`, then
`coverage.json`, `coverage/coverage-summary.json`, `coverage.out`, `lcov.info`. How each
stack produces one:

| Stack | Command | File the ratchet reads |
|---|---|---|
| Python (`STK-PY`) | `.venv/bin/pytest --cov --cov-report=json` | `coverage.json` (`totals.percent_covered`) |
| TypeScript (`STK-TS`) | `vitest run --coverage` with the `json-summary` reporter | `coverage/coverage-summary.json` (`total.lines.pct`) |
| Go (`STK-GO`) | `go test ./... -coverprofile=coverage.out` | `coverage.out` (via `go tool cover -func`) |
| Anything lcov-emitting | c8, genhtml pipelines | `lcov.info` (LH/LF aggregate) |

Because precedence is first-match, a stale `coverage.json` left over from an experiment
can shadow the real report — coverage artifacts are gitignored and cleaned before runs.
Missing data entirely is exit 2 ("run tests with coverage first"), tolerated only on
fresh scaffolds with no tests yet.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `coverage-ratchet.py --check` (exit 2 tolerated) (T2+) | current ≥ baseline − 0.1 | TST-RATCHET-01, -02 |
| 2 | `[ ! -f .coverage-baseline ] \|\| git ls-files --error-unmatch .coverage-baseline` | baseline tracked if present | TST-RATCHET-01 |
| 3 | attest: no unwaived reset/lowering (T2+) | explicit yes recorded | TST-RATCHET-03 |
| 4 | attest: coverage format readable, artifacts clean (T2+) | explicit yes recorded | TST-RATCHET-04 |

**Remediation:** FAIL below baseline → add tests for the new untested code; never edit the
baseline to pass · exit 2 with tests present → the coverage report isn't being written
(add `--cov-report=json` / `json-summary` reporter / `-coverprofile`) · baseline
untracked → `git add .coverage-baseline` · legitimate decrease (code deletion) → waiver
per TST-RATCHET-03, then re-initialize.

## Worked Example

Lifecycle of the baseline in a Python T2 project:

```
# First run — initialize and commit (development mode, no --check)
$ .venv/bin/pytest -q --cov --cov-report=json >/dev/null
$ python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py
coverage-ratchet: baseline initialized at 84.10%
$ git add .coverage-baseline && git commit -m "chore: initialize coverage baseline (84.10%)"

# Later — a feature lands with tests; the ratchet ratchets
$ python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py
coverage-ratchet: raised baseline 84.10% → 86.55%        # commit this with the feature

# Verification — read-only, tree untouched
$ python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py --check
coverage-ratchet: OK (86.55% ≥ 86.55%)

# Regression — new code, no tests
coverage-ratchet: FAIL — coverage 83.20% is below baseline 86.55%. Add tests or
(with a waiver) reset the baseline.
```

The corresponding CI step is the exact frontmatter command — `DEV-CI` wires it after the
test job so `coverage.json` already exists.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Editing `.coverage-baseline` downward to green CI | Silent drift; the gate now certifies a lie | Add tests, or waiver + reset (TST-RATCHET-03) |
| Fixed "80% required" threshold instead of a ratchet | Padding below the bar, blocked refactors above it | Ratchet against own history (TST-POLICY-05) |
| Running without `--check` in CI/verification | Baseline bump in a throwaway workspace; drift between runs | `--check` in all verification (TST-RATCHET-02) |
| Trivial assert-free tests to feed the ratchet | Coverage without verification; the number lies | Test behavior; the ratchet records honest gains only |
| Counting vendored/generated code in coverage | Baseline inflated or deflated by code nobody tests | Exclude via coverage config; waiver if baseline shifts |
| Stale `coverage.json` from an old run shadowing the real report | Ratchet grades last week's tests | Gitignore + clean coverage artifacts (TST-RATCHET-04) |

## References

- `checks/coverage-ratchet.py` — the implementation; this standard documents its
  contract (formats, precedence, tolerance, `--check`, exit codes 0/1/2).
- coverage.py JSON report / istanbul json-summary / `go tool cover` / lcov tracefile
  format — the four format contracts the reader function depends on.
- Constitution C3 — "coverage never decreases" is the article this mechanism enforces.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
