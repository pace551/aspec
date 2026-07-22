---
id: DEV-GIT
title: Git & PR Conventions
family: DEV
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - commit
  - branch
  - merge
  - rebase
  - pull request
  - pr
  - force-push
  - git history
  - conventional commits
  - pr description
requires: []
verification:
  - cmd: "sh -c 'git log -20 --pretty=%s 2>/dev/null | grep -vE \"^(feat|fix|docs|chore|refactor|test|ci|build|perf|style)([(][^)]*[)])?!?: .+|^(Merge |Revert |fixup! |squash! )\" | grep -q . && exit 1 || exit 0'"
    expect: "exit 0 — last 20 commit subjects all conventional (empty repos pass)"
    layer: G
    rules: [DEV-GIT-01]
  - cmd: "sh -c 'git rev-parse --verify -q main >/dev/null || exit 0; [ -z \"$(git log --merges -20 --pretty=%h main --)\" ]'"
    expect: "exit 0 — no merge commits in recent main history (linear)"
    layer: G
    rules: [DEV-GIT-03]
  - cmd: "sh -c 'b=$(git symbolic-ref --short -q HEAD) || exit 0; [ \"$b\" = main ] || echo \"$b\" | grep -qE \"^(feat|fix|docs|chore|refactor|test|ci|spike)/[a-z0-9][a-z0-9._-]*$\"'"
    expect: "exit 0 — current branch is main or {type}/{slug}"
    layer: G
    rules: [DEV-GIT-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: commits are small and coherent — one logical change each, no mixed refactor+feature commits"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-GIT-02]
  - cmd: "attest: all changes reached main via branch + PR, never a direct commit to main"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-GIT-05]
    tiers: [T3, T4]
  - cmd: "attest: every PR description carries evidence — what changed, why, and how it was verified (commands run + results, screenshots for UI)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-GIT-06]
    tiers: [T3, T4]
  - cmd: "attest: no commit message narrates tool/AI involvement beyond the standard trailers"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-GIT-07]
last_review: 2026-07-22
---

# Git & PR Conventions (DEV-GIT)

## Abstract

Codifies house git hygiene (Constitution C4): conventional commits, small coherent
commits, linear history via rebase-merge, no force-push to shared branches, `{type}/{slug}`
branch names, and — at T3+ — no direct commits to `main`: every change rides a PR even
solo, because the PR is the review surface `/code-review` operates on. PR descriptions
carry *evidence* (commands run and their results, screenshots for UI), never adjectives.
Commit messages describe the change, not the tooling that produced it.

## Normative Rules

### DEV-GIT-01 — Commit messages MUST follow Conventional Commits

**Tiers**: all required — **Layer**: G

Format: `{type}({scope})?: {imperative summary}` with type ∈ `feat` `fix` `docs` `chore`
`refactor` `test` `ci` (plus `build`/`perf`/`style` where apt). Scope is optional but
encouraged on multi-module repos. `Merge`/`Revert`/`fixup!` machine prefixes are exempt.
The type is a claim: `fix:` implies a failing test existed first (C3, TST-POLICY);
`refactor:` implies no behavior change. The verification samples the last 20 subjects, so
one-off legacy history doesn't poison a repo forever.

### DEV-GIT-02 — Commits SHOULD be small and coherent — one logical change each

**Tiers**: all advisory — **Layer**: A (attestation)

A commit is one revertable idea: rename in one commit, behavior change in the next.
"Small" is measured in concepts, not lines — a mechanical 500-file rename is one
coherent commit; a 30-line diff mixing a bugfix with an unrelated cleanup is two. If the
summary needs "and", split it.

### DEV-GIT-03 — History on `main` MUST be linear; shared branches MUST NOT be force-pushed

**Tiers**: all required — **Layer**: G

Merge strategy is rebase-merge (GitHub "Rebase and merge"), so `main` is a straight line
and `git bisect`/`revert` stay trivial. Force-push is fine on *your own unshared feature
branch* (rewriting before review is good hygiene); it is never fine on `main` or any
branch someone else — including a CI run or another agent session — may have fetched.
The G check asserts no merge commits in recent `main` history.

### DEV-GIT-04 — Branch names MUST follow `{type}/{slug}`

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

Types mirror commit types (`feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`,
`ci/`, plus `spike/` for throwaway exploration); slug is short kebab-case
(`feat/grace-period`, `fix/tz-naive-datetime`). The branch name should predict the
eventual squash/PR title. Working directly on `main` is tolerated only where DEV-GIT-05
allows it.

### DEV-GIT-05 — At T3+, changes MUST NOT be committed directly to `main` — branch + PR, even solo

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The PR is not ceremony; it is the review surface: `/code-review` and `/security-review`
(DEV-REVIEW) attach findings to it, CI gates it (DEV-CI), and the description archives
the evidence. Solo development doesn't change that — future-James is the second party.
At T4, GitHub branch protection with required status checks makes this mechanical
(DEV-CI-05). At T1/T2, committing to `main` is allowed but PRs are still the default for
anything non-trivial.

### DEV-GIT-06 — PR descriptions MUST carry evidence: what changed, why, and how it was verified

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Knox-style evidence: the exact commands run and their observed results (test output
counts, exit codes), screenshots or recordings for anything visual, and links to the spec
or issue for the why. "Works great", "thoroughly tested", "should be fine" are adjectives,
not evidence — a claim without an executed command behind it doesn't belong in the
description (Constitution C2). Applies to any PR at any tier once one exists.

### DEV-GIT-07 — Commit messages MUST NOT narrate tool or AI involvement beyond the standard trailers

**Tiers**: all required — **Layer**: A (attestation)

The standard `Co-Authored-By:` / session trailers are the sanctioned, machine-readable
record of agent involvement. Beyond those, messages describe the change itself — never
"asked Claude to…", "AI-generated fix", or tool play-by-play. History documents *what
changed and why*; provenance lives in trailers where tooling can parse it.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | last-20 commit subjects vs conventional grammar | exit 0 (no offenders; empty repo passes) | DEV-GIT-01 |
| 2 | `git log --merges main` recent window empty | exit 0 (linear history) | DEV-GIT-03 |
| 3 | current branch is `main` or `{type}/{slug}` (T2+) | exit 0 | DEV-GIT-04 |
| 4–7 | attestation checklist (one per rule) | explicit yes recorded | DEV-GIT-02, -05, -06, -07 |

**Remediation:** non-conventional subjects on an unpushed branch → `git rebase main -x` /
reword; already on `main` → leave them, conform from now (the 20-subject window ages them
out) · merge commit on main → switch the repo to rebase-merge in GitHub settings; don't
rewrite pushed history to erase it · misnamed branch → `git branch -m feat/new-name`.

## Worked Example

A compliant commit and its PR description:

```
fix(scheduler): treat naive datetimes from settings.yaml as America/Chicago

Naive values silently compared false against aware run timestamps,
skipping the grace-period check (bug #12).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

```markdown
## What
Grace-period check no longer skipped when settings.yaml omits a timezone.

## Why
Bug #12 — payment marked late despite the 3-day grace window.

## Evidence
- new failing-first test: `tests/test_grace.py::test_naive_tz` (red at a1b2c3d, green now)
- `.venv/bin/pytest -q` → 34 passed
- `.venv/bin/ruff check .` → exit 0
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `git commit -m "fix stuff"` | Untyped, unscoped, unsearchable | `fix(scope): what actually changed` |
| Feature + drive-by refactor in one commit | Revert of either takes both; review noise | Two commits, `refactor:` first |
| GitHub default merge button (merge commit) | Non-linear main; bisect walks merge bubbles | Repo setting: rebase-merge only |
| Force-push to main "to clean up" | Every clone/CI/agent session now diverges | Revert forward; history is append-only |
| PR body: "tested, works great" | Adjectives, not evidence — unverifiable claim | Commands + observed results (DEV-GIT-06) |
| "Used Claude to refactor the parser" in a subject | Narrates tooling, not the change | `refactor(parser): …` + standard trailer |
| Solo T3 repo committing straight to main | No review surface, no CI gate, no evidence trail | Branch + PR even solo (DEV-GIT-05) |

## References

- Conventional Commits 1.0.0 (conventionalcommits.org) — the exact grammar DEV-GIT-01
  enforces.
- Constitution C4 — this standard is its detail expansion.
- GitHub docs, "About protected branches" — the enforcement backstop for DEV-GIT-05 at T4
  (wired in DEV-CI-05).
- DEV-REVIEW — why the PR must exist: it is where review findings live.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
