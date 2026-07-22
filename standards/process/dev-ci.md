---
id: DEV-CI
title: CI Baseline
family: DEV
version: 1.0.0
status: active
tiers:
  T1: n/a
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - ci
  - github actions
  - workflow
  - pipeline
  - continuous integration
  - branch protection
  - status checks
  - merge gate
  - red build
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/dev-ci-present.sh --tier T3"
    expect: "exit 0 — workflows declare lint, typecheck, test, coverage-ratchet, gitleaks, sast, sca"
    layer: G
    rules: [DEV-CI-01]
    tiers: [T3]
  - cmd: "bash ~/Dev/claude-code/governance/checks/dev-ci-present.sh --tier T4"
    expect: "exit 0 — T3 set plus license-audit"
    layer: G
    rules: [DEV-CI-01]
    tiers: [T4]
  - cmd: "sh -c '[ -x .git/hooks/pre-commit ] && [ -x .git/hooks/pre-push ]'"
    expect: "exit 0 — hooks installed and executable (the T1/T2 gate carrier)"
    layer: G
    rules: [DEV-CI-02]
  - cmd: "attest: conditional fragments are wired where the surface exists (iac-scan for infra, a11y + lighthouse for web)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-CI-03]
    tiers: [T3, T4]
  - cmd: "attest: nothing merged on red — the tier's gate set was green for every merge, and any red main was treated as the top-priority fix"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-CI-04]
  - cmd: "attest: main has branch protection with the ci jobs as required status checks"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-CI-05]
    tiers: [T4]
last_review: 2026-07-22
---

# CI Baseline (DEV-CI)

## Abstract

The non-negotiable automated gate set per tier, composed from `templates/ci/_fragments/`.
T1 runs no CI — the git hooks *are* the gates. T2 makes CI optional but hooks mandatory,
plus a reproducibility check. T3 makes CI mandatory on PR and `main`: lint, typecheck,
test, coverage-ratchet, gitleaks, SAST, SCA — with iac-scan for infra and
a11y/lighthouse for web surfaces. T4 adds license-audit and enforces it all via required
status checks. Everywhere: green to merge, and a red `main` outranks all feature work.
`checks/dev-ci-present.sh` audits the job set.

## Normative Rules

### DEV-CI-01 — CI MUST run the tier's job set, composed from `templates/ci/_fragments/`

**Tiers**: T1 n/a · T2 advisory · T3–T4 required — **Layer**: G

| Tier | Required jobs (fragment names) |
|---|---|
| T1 | none — hooks carry the gates (DEV-CI-02) |
| T2 | none required; if CI exists, at minimum `test` + a reproducibility check (clean-checkout install from lockfile, then tests) |
| T3 | `lint`, `typecheck`, `test`, `coverage-ratchet`, `gitleaks`, `sast`, `sca` — on `pull_request` and push to `main` |
| T4 | T3 set + `license-audit` |

Jobs are composed from the fragment library (`lint.yml`, `typecheck.yml`, `test.yml`,
`coverage-ratchet.yml`, `gitleaks.yml`, `sast.yml`, `sca.yml`, `iac-scan.yml`,
`a11y.yml`, `lighthouse.yml`, `license-audit.yml`) rather than hand-rolled per repo, so
a fragment fix propagates. Job names stay equal to fragment names — that identity is
what `dev-ci-present.sh` greps for. Untyped stacks satisfy `typecheck` with the
fragment's no-op variant rather than dropping the job name.

### DEV-CI-02 — Git hooks MUST carry the gates where CI does not

**Tiers**: all required — **Layer**: G

Pre-commit: format + lint + secret scan. Pre-push: tests + coverage ratchet. At T1/T2
these hooks are the *entire* enforcement story, which is why they're required at every
tier and installed at bootstrap (DEV-BOOTSTRAP-06) — CI at T3+ is a second, unskippable
copy of the same gates, not a replacement for fast local feedback. Hook sources:
`templates/scaffolds/_common/`.

### DEV-CI-03 — Conditional fragments MUST be wired where the surface exists

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Repo contains Terraform/IaC → add `iac-scan`. Repo serves a browser-facing surface →
add `a11y` and `lighthouse` (budgets owned by UX-A11Y / OPS-PERF). The trigger is the
*surface*, not the tier: a T3 API with no frontend legitimately omits a11y, and the
attestation says so explicitly rather than silently.

### DEV-CI-04 — The gate set MUST be green to merge; a red `main` is the top-priority fix

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

"Green to merge" means the tier's full gate set — CI at T3+, hooks at T1/T2 — with no
merged-on-red exceptions; an emergency merge over a red gate is a waiver with expiry
(C9), not a habit. When `main` goes red, fixing it preempts feature work: every branch
cut from a red `main` inherits the breakage, and the ratchet/gitleaks gates stop
meaning anything the moment red is normal. Fix forward or revert within the day.

### DEV-CI-05 — At T4, `main` MUST be protected with required status checks

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

GitHub branch protection on `main`: the DEV-CI-01 jobs listed as required status checks,
force-pushes and deletions blocked, and the rules applied to administrators — solo repos
have exactly one admin, so an admin bypass is no protection at all. This is the
mechanical backstop for DEV-GIT-05 (no direct commits to `main`): at T4 the platform
enforces what T3 takes on attestation.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/dev-ci-present.sh --tier T3` (T3) | exit 0 — required job names found | DEV-CI-01 |
| 2 | `bash ~/Dev/claude-code/governance/checks/dev-ci-present.sh --tier T4` (T4) | exit 0 — T3 set + license-audit | DEV-CI-01 |
| 3 | `[ -x .git/hooks/pre-commit ] && [ -x .git/hooks/pre-push ]` | exit 0 | DEV-CI-02 |
| 4 | attestation: conditional fragments match the repo's surfaces (T3+) | explicit yes | DEV-CI-03 |
| 5 | attestation: green-to-merge held; red main treated as top priority | explicit yes | DEV-CI-04 |
| 6 | attestation: branch protection + required checks (T4) | explicit yes | DEV-CI-05 |

**Remediation:** missing jobs → copy the named fragments from `templates/ci/_fragments/`
into `.github/workflows/` and reference them from `ci.yml` (worked example) · hooks
missing → `/bootstrap-repo` retrofit (DEV-BOOTSTRAP-06) · red main → stop, revert or fix
forward today · protection absent at T4 → GitHub → Settings → Branches → add rule for
`main`, tick "require status checks" and select the DEV-CI-01 jobs.

## Worked Example

A T3 repo's `ci.yml`, composing local copies of the fragments as reusable workflows:

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  lint:
    uses: ./.github/workflows/lint.yml
  typecheck:
    uses: ./.github/workflows/typecheck.yml
  test:
    uses: ./.github/workflows/test.yml
  coverage-ratchet:
    uses: ./.github/workflows/coverage-ratchet.yml
  gitleaks:
    uses: ./.github/workflows/gitleaks.yml
  sast:
    uses: ./.github/workflows/sast.yml
  sca:
    uses: ./.github/workflows/sca.yml
```

`dev-ci-present.sh --tier T3` passes on this repo three ways over: job keys, `uses:`
lines, and the fragment files themselves. Promotion to T4 is one job
(`license-audit`) plus the branch-protection rule.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Hand-rolled per-repo workflow YAML | Fragment fixes never propagate; drift per repo | Compose `templates/ci/_fragments/` (DEV-CI-01) |
| Renaming jobs ("checks", "quality") | Audit tooling and required-checks lists go blind | Job name = fragment name |
| CI as replacement for hooks at T3 | 10-minute feedback loop for a 10-second lint error | Hooks stay; CI is the unskippable copy (DEV-CI-02) |
| Merging on red "just this once" | Red becomes ambient; gates stop gating | Waiver with expiry, or don't merge (DEV-CI-04) |
| Skipping a flaky test to go green | Converts a signal into a lie; the flake is a bug | Fix or quarantine with an issue + expiry |
| T4 branch protection excluding admins | Solo repo: the only committer is the admin | "Include administrators" on (DEV-CI-05) |
| a11y job on an API-only repo | Perma-red or no-op noise; erodes trust in gates | Conditional fragments follow the surface (DEV-CI-03) |

## References

- `templates/ci/_fragments/` — the fragment library this standard composes (authored by
  the CI workstream; names are the contract).
- `checks/dev-ci-present.sh` — the G-layer auditor for DEV-CI-01.
- GitHub docs, reusable workflows + "About protected branches" — the composition and
  enforcement mechanisms for DEV-CI-01/05.
- DEV-BOOTSTRAP-06 / TST-RATCHET / SEC-SECRETS / SEC-SUPPLY — the standards whose gates
  the job set executes (hooks, coverage ratchet, gitleaks, SCA).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
