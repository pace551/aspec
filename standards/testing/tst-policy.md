---
id: TST-POLICY
title: Test Policy
family: TST
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - test
  - tests
  - tdd
  - test-first
  - bugfix
  - bug fix
  - regression
  - unit test
  - coverage
  - business logic
requires: []
verification:
  - cmd: "attest: every bugfix in this changeset began with a failing test reproducing the bug (test commit precedes or accompanies the fix commit)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-POLICY-01]
  - cmd: "attest: new core/business logic was written test-first, not tested after the fact"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-POLICY-02]
  - cmd: "attest: code left untested is genuinely glue/scaffolding/UI wiring, not core logic in disguise"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-POLICY-03]
  - cmd: "attest: test depth matches the tier expectations table (TST-POLICY-04)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-POLICY-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: no fixed coverage percentage is used as a target or gate anywhere in the project — the ratchet is the only coverage mechanism"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-POLICY-05]
last_review: 2026-07-22
---

# Test Policy (TST-POLICY)

## Abstract

The framework's testing philosophy, detailing Constitution C3. Test-first is mandatory in
exactly two places: core/business logic (logic whose wrongness produces plausible wrong
outputs rather than crashes) and every bugfix (the failing reproduction test precedes the
fix, at all tiers). Glue, scaffolding, and UI wiring may be tested after the fact — or, at
T1/T2, not at all. There is no fixed coverage percentage anywhere; `TST-RATCHET` is the
only coverage mechanism. Enforcement is mostly attestation: the practice is observable in
git history, where the test commit precedes or accompanies the fix commit (`DEV-GIT`
commit discipline is what makes that evidence legible).

## Normative Rules

### TST-POLICY-01 — Every bugfix MUST begin with a failing test that reproduces the bug

**Tiers**: all required — **Layer**: A (attestation; observable in git history)

No exceptions by tier, size, or urgency: before the fix is written, a test exists that
fails for the reason the bug report describes, and the fix makes it pass. The test commit
precedes or shares a commit with the fix (conventional-commit history per `DEV-GIT` makes
this auditable: `test:` then `fix:`, or one `fix:` containing both). A bug that can't be
reproduced in a test isn't understood yet — reproducing it *is* the diagnosis. The only
sanctioned escape is a bug in code that is itself being deleted.

### TST-POLICY-02 — New core/business logic MUST be developed test-first

**Tiers**: all required — **Layer**: A (attestation)

**Core logic** = logic whose wrongness produces wrong outputs rather than crashes:
parsers, calculators, state machines, money and date math, anything with branching
business rules. Glue fails loudly (import errors, wiring exceptions); core logic fails
silently with plausible-looking wrong answers — which is why it gets the failing test
before the implementation. Write the test from the spec, watch it fail, then implement.
At T2, the analytical core (signal computation, statistics, data transforms) is core
logic by definition — a wrong number *is* the failure mode.

### TST-POLICY-03 — Glue, scaffolding, and UI wiring MAY be tested after the fact or, at T1/T2, not at all

**Tiers**: all advisory — **Layer**: A (attestation)

Glue = code whose failure is loud and local: argument parsing hookup, DI wiring, route
registration, config loading, UI event plumbing. Testing it first buys little because it
can't be quietly wrong. At T3+ it SHOULD still get after-the-fact coverage on error paths
(what happens when config is missing), because loud failures in front of users are still
failures. The attestation exists to keep this honest: the classification "glue" is the
easiest place to hide untested core logic — a "config loader" that applies defaults and
merges overrides is a parser, and parsers are core.

### TST-POLICY-04 — Test depth MUST scale with tier

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

| Tier | Expected depth |
|---|---|
| T1 | Core logic + bugfix repros. Happy path suffices elsewhere. |
| T2 | + edge cases on the analytical core (boundary dates, empty inputs, NaN/None), seeded reproducibility (`TST-FIXTURES`), property-style checks where invariants exist (e.g. conservation: debits = credits). |
| T3 | + integration coverage on critical paths (`TST-INTEG`), error-path tests at every external boundary (API down, malformed response, timeout). |
| T4 | + invariant tests on money/ledger code, migration up-and-down tests, authz edge cases (wrong user, expired session, replay). |

Depth is cumulative; each tier includes the rows above it.

### TST-POLICY-05 — A fixed coverage percentage MUST NOT be used as a target or gate

**Tiers**: all required — **Layer**: A (attestation)

No "80% or fail" thresholds in CI, pyproject, or anywhere else. Fixed targets create
padding (asserting getters) below the bar and block honest refactors above it. The only
coverage mechanism is the ratchet (`TST-RATCHET`): coverage never drops below the
committed baseline, whatever that baseline honestly is. Coverage numbers are a *map* of
what's untested, read when deciding what to test next — never a goal.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: bugfixes began with a failing repro test | explicit yes recorded | TST-POLICY-01 |
| 2 | attest: core logic written test-first | explicit yes recorded | TST-POLICY-02 |
| 3 | attest: untested code is genuinely glue | explicit yes recorded | TST-POLICY-03 |
| 4 | attest: depth matches the tier table (T2+) | explicit yes recorded | TST-POLICY-04 |
| 5 | attest: no fixed coverage target exists | explicit yes recorded | TST-POLICY-05 |

**Remediation:** fix landed without a repro test → write the test now, confirm it fails
against the pre-fix code (`git stash` the fix or check out the parent commit), then
recommit in order · untested "glue" turns out to branch on business rules → reclassify as
core, test it before the next change touches it · a coverage threshold found in CI config
→ delete it, run the ratchet once to set the honest baseline.

## Worked Example

A bugfix under this policy, as it appears in history (`DEV-GIT` conventional commits):

```
$ git log --oneline -- src/sched/ tests/
9f21c4a fix: roll payment date forward, not backward, across DST gap (#14)
b7e03d1 test: failing repro — payment due 2026-03-08 rolls to 03-07 across DST
```

The repro test, written first, failing before `9f21c4a`:

```python
def test_due_date_rolls_forward_across_dst_gap():
    # Bug #14: 2026-03-08 02:30 does not exist in America/New_York
    due = next_due_date(date(2026, 2, 8), tz="America/New_York")
    assert due == date(2026, 3, 9)   # was returning 2026-03-07
```

Date math is core logic (TST-POLICY-02): the buggy version returned a *plausible* date,
crashed nothing, and would have silently mischarged — exactly the failure class test-first
exists to catch.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Fix first, "I'll add the test after" | The after-test is written to pass, not to reproduce; it often asserts the fix, not the bug | Failing repro before the fix (TST-POLICY-01) |
| Deleting or skipping the failing test to ship | The bug is now invisible and will return | Fix the code or waive visibly (C9) |
| Labeling business rules "glue" to skip testing | Silent wrong-output code with zero coverage | Classify by failure mode, not by file name (TST-POLICY-02/03) |
| Coverage-driven test padding (getters, `__repr__`) | Raises the number, tests nothing that can be wrong | Test core logic edges; let the ratchet record honest gains |
| One giant test asserting the whole output blob | Fails for every reason, diagnoses none | One behavior per test; name states the expected behavior |
| Repro test that passes against the pre-fix code | It reproduces nothing | Run it before applying the fix; it MUST fail first |

## References

- Constitution C3 — the article this standard details; the ratchet mechanics live in
  `TST-RATCHET`.
- Kent Beck, *Test-Driven Development: By Example* — the red-green discipline
  TST-POLICY-02 applies, scoped to where it pays.
- Michael Feathers, *Working Effectively with Legacy Code* — characterization tests as
  the entry move when a bugfix lands in untested core.
- `DEV-GIT` — commit conventions that make test-before-fix auditable in history.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
