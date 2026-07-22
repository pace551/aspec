---
id: DEV-REVIEW
title: Code Review
family: DEV
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - code review
  - review
  - pull request
  - pr review
  - security review
  - simplify
  - bugfix
  - merge
requires: []
verification:
  - cmd: "attest: every merged change received the review rung for this tier (T1 /simplify or self-review · T2 /code-review medium on analytical core · T3 /code-review high per PR · T4 high per PR + ultra for major features)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-REVIEW-01]
  - cmd: "attest: every change touching auth, input handling, or crypto received /security-review"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-REVIEW-02]
    tiers: [T3, T4]
  - cmd: "attest: every review finding was fixed or explicitly declined with a written reason on the PR — none silently ignored"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-REVIEW-03]
  - cmd: "attest: every bugfix review confirmed a failing test existed before the fix"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-REVIEW-04]
last_review: 2026-07-22
---

# Code Review (DEV-REVIEW)

## Abstract

Solo development does not mean unreviewed development — it means the reviewer is a
skill invocation instead of a colleague. This standard fixes the review ladder per tier
(from self-review of the diff at T1 up to cloud multi-agent review at T4), mandates
`/security-review` for sensitive-surface changes at T3+, and sets the one process
invariant that makes review worth anything: every finding is either fixed or explicitly
declined with a reason on the PR. A finding that is silently ignored converts the review
into theater.

## Normative Rules

### DEV-REVIEW-01 — Every change MUST receive its tier's review rung before merge

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

| Tier | Minimum rung | Surface |
|---|---|---|
| T1 | `/simplify`, or self-review of the full diff before commit | working tree |
| T2 | `/code-review` (medium effort) on the analytical core | working tree or PR |
| T3 | `/code-review` high effort on **every** PR | the PR (DEV-GIT-05) |
| T4 | T3, **plus** `/code-review` ultra (cloud multi-agent) for major features, pre-merge | the PR |

"Analytical core" at T2 means the code whose correctness the research conclusion depends
on — signal construction, statistics, data joins — not plotting glue. "Major feature" at
T4 means anything a user would notice or that touches money paths. Self-review at T1 is
real review: read every hunk of the diff, not the vibes of the session.

### DEV-REVIEW-02 — Changes touching auth, input handling, or crypto MUST receive `/security-review`

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Triggering surfaces: authentication/session logic, anything parsing untrusted input
(request bodies, file uploads, webhooks, scraped content), cryptographic operations or
key handling, and permission/authorization checks. `/security-review` runs *in addition
to* the DEV-REVIEW-01 rung, on the same PR. When in doubt whether a change "touches"
such a surface, it does — the review is cheaper than the doubt.

### DEV-REVIEW-03 — Review findings MUST be fixed or explicitly declined with a reason — never silently ignored

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Every finding gets one of exactly two outcomes, recorded where the review happened
(PR comment/description, or commit body for T1 self-review): **fixed** (with the fixing
commit) or **declined** with a substantive reason ("false positive because…", "deferred
to #14 because…"). "Declined: disagree" is not a reason. A declined finding that recurs
across projects is a signal for `/evolve-standards`, not a nuisance to keep re-declining.

### DEV-REVIEW-04 — Bugfix reviews MUST confirm the failing-test-first rule was followed

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

For any `fix:` change, the reviewer's first check is TST-POLICY / Constitution C3: does a
test exist that failed before the fix and passes after? The PR evidence section
(DEV-GIT-06) should name the test and the red→green commits. A bugfix without a
regression test is an unfinished bugfix — the review outcome is "fix the process gap",
not "looks correct to me".

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attestation: tier's review rung ran on every merged change | explicit yes | DEV-REVIEW-01 |
| 2 | attestation: sensitive-surface changes got `/security-review` (T3+) | explicit yes | DEV-REVIEW-02 |
| 3 | attestation: findings fixed or declined-with-reason | explicit yes | DEV-REVIEW-03 |
| 4 | attestation: bugfix reviews checked failing-test-first | explicit yes | DEV-REVIEW-04 |

**Remediation:** merged without review → run the rung retroactively on the merge commit
range and file follow-up fixes; note the miss in GOVERNANCE.md (C9) · unaddressed
findings discovered later → triage each to fixed/declined now, on the original PR ·
bugfix landed without a test → add the regression test immediately; it must fail when the
fix is reverted.

## Worked Example

A T3 PR review cycle, end to end:

```text
1. PR opened: feat/webhook-intake (DEV-GIT-05)
2. /code-review high  → 3 findings (R1 correctness, R2 naming, R3 missing timeout)
3. /security-review   → 1 finding (S1: webhook signature not verified) — input surface
4. Outcomes, recorded as PR comments:
   R1: fixed in 4f2a91c
   R3: fixed in 8c07d2e
   S1: fixed in b3e1f00 (HMAC check + test)
   R2: Declined — matches the module's existing naming; renaming half the
       symbols is churn without a bug. Tracked for the next refactor pass (#14).
5. CI green (DEV-CI) → rebase-merge.
```

The decline in step 4 is compliant: explicit, reasoned, and recorded on the PR.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Merging, then reviewing "when there's time" | Findings arrive after the blast radius exists | Review is pre-merge, always (DEV-REVIEW-01) |
| Re-running review until it comes back clean | Selection over runs ≠ fixing; findings were real | Address each finding from the first run |
| Silently dropping a finding you disagree with | Next session re-litigates it from scratch | Decline with a reason, on the PR (DEV-REVIEW-03) |
| Skipping `/security-review` because "it's just a form field" | Input handling is exactly the trigger | Sensitive surface ⇒ review, no size threshold |
| T1 "self-review" = skimming the session summary | Summaries hide diffs; bugs live in hunks | Read the actual diff, hunk by hunk |
| Approving a bugfix with tests written after the fix | Test may encode the bug's behavior, not the spec | Failing-first or it isn't done (DEV-REVIEW-04) |

## References

- `/code-review`, `/simplify`, `/security-review` skills — the mechanisms this ladder is
  built from; effort levels are theirs, the ladder mapping is this standard's.
- Constitution C2/C3 — verified-done and test-first, which rules 03/04 operationalize in
  review.
- TST-POLICY — owns the failing-test-first rule that DEV-REVIEW-04 checks.
- Google Engineering Practices, "Code Review Developer Guide" — the fixed-or-declined
  discipline (every comment resolved) adapted to solo scale.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
