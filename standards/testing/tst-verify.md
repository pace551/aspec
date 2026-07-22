---
id: TST-VERIFY
title: Verification-First Delivery
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
  - verify
  - verification
  - done
  - ship
  - completion
  - gate
  - smoke test
  - it works
  - end-to-end
  - checklist
requires: []
verification:
  - cmd: "attest: every rung of the gate ladder was executed in order — typecheck/lint, unit tests, integration where present, end-to-end via the real interface, /verify-compliance"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-VERIFY-01]
  - cmd: "attest: the change was exercised through its real interface (CLI run / endpoint hit / UI driven), not only through its tests"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-VERIFY-02]
  - cmd: "sh -c '[ -f scripts/verify.sh ] || [ -d .github/workflows ]'"
    expect: "exit 0 — verification commands have a scripted home (T3+, where CI is mandatory)"
    layer: G
    rules: [TST-VERIFY-03]
    tiers: [T3, T4]
  - cmd: "attest: verification commands were taken from scripts/CI/CLAUDE.md, not re-derived ad hoc this session"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-VERIFY-03]
  - cmd: "attest: the completion summary states what was executed and what was NOT, and every claim in it traces to an executed command"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-VERIFY-04]
last_review: 2026-07-22
---

# Verification-First Delivery (TST-VERIFY)

## Abstract

The generalized knox gate ladder, and the standard Constitution C2 summarizes: work is
done when verification says so, not when the code looks right. "Done" means five rungs
executed in order — typecheck/lint, unit tests, integration tests where they exist, the
change exercised end-to-end through its real interface, and `/verify-compliance` green.
Deterministic scripts verify; the LLM complies: the commands live in scripts and CI, never
re-derived per session. Completion claims report confidence honestly — what ran, what
didn't — and every claim traces to an executed command. This is the standard
`/implement-spec`'s final gate cites. Applies at every tier; a T1 "it works" still
requires having run it.

## Normative Rules

### TST-VERIFY-01 — "Done" MUST mean every rung of the gate ladder executed, in order

**Tiers**: all required — **Layer**: A (attestation)

The ladder, bottom to top:

1. **Typecheck/lint** — the stack's static gates (`ruff`/`mypy`, `tsc`/`eslint`,
   `go vet`) exit 0.
2. **Unit tests** — the full suite, not the subset near the change.
3. **Integration tests** — where they exist (`TST-INTEG`); "none exist" is a valid rung
   outcome, "didn't run them" is not.
4. **End-to-end via the real interface** — TST-VERIFY-02.
5. **`/verify-compliance` green** — the project's tier-selected standards pass.

In order, because each rung is cheaper than the next and a lint failure invalidates
everything above it. A failed rung stops the ladder: fix, restart from that rung. A
deliberately skipped rung is not "done" — it is "done except X", said out loud (C9), with
the skip and its reason in the completion summary.

### TST-VERIFY-02 — The change MUST be exercised end-to-end through its real interface, not only through tests

**Tiers**: all required — **Layer**: A (attestation)

Tests exercise the code; rung 4 exercises the *product*. Run the actual CLI with real
arguments and read its output; start the server and hit the endpoint with `curl`; drive
the UI and watch the behavior change; for a scheduled job, trigger the entry point the
scheduler uses (the mortgage-scheduler launchd failures lived precisely in the gap
between "tests green" and "runs under launchd"). Observe the new behavior specifically —
not just "it starts". Where the real interface has external side effects, use its dry-run
mode until the C7 human go exists; "dry-run exercised, live path not" is then the honest
confidence statement per TST-VERIFY-04.

### TST-VERIFY-03 — Verification commands MUST live in scripts/CI, never re-derived ad hoc per session

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation) + G (T3+ scripted home exists)

Deterministic scripts verify; the LLM complies. The commands that constitute "verified"
are written down once — `scripts/verify.sh`, the CI workflow (`DEV-CI`), the project
`CLAUDE.md` command list, the standard's own frontmatter — and every session runs those,
byte for byte (`.venv/bin/pytest -q`, per `STK-PY-08`, not whatever pytest invocation
comes to mind). A session that improvises its own verification can improvise one that
passes; drift hides in the delta between what was run and what should have been. New
verification needs are added to the scripts first, then run.

### TST-VERIFY-04 — Completion claims MUST state what was executed and what was NOT

**Tiers**: all required — **Layer**: A (attestation)

Every claim in a completion summary traces to a command that actually ran, with its
observed result — "42 passed", "HTTP 200 with the new field", not "should work".
Confidence is reported explicitly: "tests green; not exercised against the live API",
"verified on macOS only". Anything not verified is marked as such, prominently, not
omitted — an unverified claim stated as fact is the failure mode C2 exists to kill.
"Verification failed and here's the output" is always an acceptable report;
"success" on inference never is.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: full ladder executed in order | explicit yes recorded | TST-VERIFY-01 |
| 2 | attest: real interface exercised | explicit yes recorded | TST-VERIFY-02 |
| 3 | `[ -f scripts/verify.sh ] \|\| [ -d .github/workflows ]` (T3+) | a scripted home exists | TST-VERIFY-03 |
| 4 | attest: commands from scripts/CI, not ad hoc | explicit yes recorded | TST-VERIFY-03 |
| 5 | attest: summary separates executed from not-executed | explicit yes recorded | TST-VERIFY-04 |

**Remediation:** rung skipped for time → say so in the summary and finish the ladder
before calling it done · no way to exercise the real interface → build the dry-run/local
harness first; that gap is itself a finding · verification commands scattered or ad hoc →
consolidate into `scripts/verify.sh` and reference it from `CLAUDE.md` · summary claim
without a command behind it → run the command or reword the claim as unverified.

## Worked Example

A completion summary that satisfies TST-VERIFY-04 — every line traceable, gaps explicit:

```markdown
## Verified (executed, in order)
1. `.venv/bin/ruff check . && .venv/bin/ruff format --check .` — exit 0
2. `.venv/bin/pytest -q` — 42 passed (includes new failing-first repro for #14)
3. `.venv/bin/pytest tests/integration -q` — 6 passed (real SQLite)
4. `.venv/bin/python -m sched run --dry-run --date 2026-03-09` — printed the
   corrected DST-adjusted due date 2026-03-09 (was 2026-03-07 before the fix)
5. `/verify-compliance` — green; 2 advisory attestations recorded

## NOT verified
- Live payment-provider call (dry-run only; C7 approval not yet granted)
- Behavior under launchd (will confirm at tonight's scheduled run)
```

Contrast the banned version: "Fixed the DST bug, everything works now." — zero executed
commands, two unverifiable claims.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Should work now" / success by inference | The claim is a prediction wearing a checkmark | Run it; report what was observed (TST-VERIFY-04) |
| Tests green, program never run | Tests encode expectations, not reality — wiring, env, and launchd live outside them | Rung 4: real interface, real invocation (TST-VERIFY-02) |
| Verifying by re-reading the diff | Review is not execution; C2 requires executed evidence | Execute the ladder (TST-VERIFY-01) |
| Running only tests "near" the change | The regression is always in the file you didn't run | Full suite; that's what rung 2 means |
| Re-deriving verification commands each session | Drift between sessions; convenient commands pass conveniently | Scripts/CI are the source of truth (TST-VERIFY-03) |
| Burying one red check under twenty green lines | Summary reads as success; the failure ships | Failures and skips first, prominently (TST-VERIFY-04) |
| Skipping rung 4 because "unit tests cover it" | The mortgage-scheduler class of bug: correct code, broken invocation | Exercise the deployed entry point |

## References

- Constitution C2 — the one-paragraph summary of this standard; TST-VERIFY is its
  detail.
- `/implement-spec` skill — its final Verify step cites this standard as the definition
  of done.
- `DEV-CI` — where the scripted verification commands run automatically at T3+.
- The mortgage-scheduler launchd incident (repo history) — the house scar tissue behind
  TST-VERIFY-02: tests passed for weeks while the real entry point failed.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
