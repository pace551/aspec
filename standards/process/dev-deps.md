---
id: DEV-DEPS
title: Dependency Management
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
  - dependency
  - dependencies
  - upgrade
  - update
  - renovate
  - dependabot
  - lockfile
  - package
  - version bump
  - npm install
  - pip install
  - sdk version
  - model version
requires: []
verification:
  - cmd: "sh -c '[ ! -f package.json ] || [ -f package-lock.json ] || [ -f pnpm-lock.yaml ] || [ -f yarn.lock ] || [ -f bun.lock ]'"
    expect: "exit 0 — a JS/TS project commits its lockfile"
    layer: G
    rules: [DEV-DEPS-01]
    tiers: [T2, T3, T4]
  - cmd: "attest: every project with dependencies commits a lockfile for its ecosystem (python apps per STK-PY-06)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DEPS-01]
  - cmd: "sh -c '[ -f renovate.json ] || [ -f renovate.json5 ] || [ -f .github/renovate.json ] || [ -f .github/renovate.json5 ] || [ -f .renovaterc ] || [ -f .renovaterc.json ] || [ -f .github/dependabot.yml ] || [ -f .github/dependabot.yaml ]'"
    expect: "exit 0 — Renovate (or Dependabot) config present"
    layer: G
    rules: [DEV-DEPS-02]
    tiers: [T3, T4]
  - cmd: "attest: major-version updates were merged only after reading the changelog/release notes"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DEPS-03]
  - cmd: "attest: each new dependency was weighed against stdlib/existing deps, with maintenance signals and license checked"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DEPS-04]
  - cmd: "attest: no current-version/model/pricing fact was answered from memory — registry or official docs consulted at time of use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DEPS-05]
  - cmd: "attest: fast-moving tools (ai sdks, model ids) got their monthly fast-lane review via /evolve-standards"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DEPS-06]
last_review: 2026-07-22
---

# Dependency Management (DEV-DEPS)

## Abstract

Dependencies are the code you ship but didn't write: this standard keeps them
reproducible (lockfiles everywhere), current (Renovate at T3+, auto-merge for small
CI-green updates, majors always read-then-reviewed), and deliberate (adding a dep is a
decision with maintenance and license checks, not a reflex). Plus the house epistemics
rule: current versions, model names, and pricing are looked up at time of use, never
recalled from memory (Constitution C8). Vulnerability scanning of what's installed is
SEC-SUPPLY / stack standards; this doc owns cadence and choice.

## Normative Rules

### DEV-DEPS-01 — Lockfiles MUST be committed in every project with dependencies

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

The lockfile is what makes "works on my machine" a transferable fact — to CI, to launchd,
to a re-clone two years out. JS/TS: `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`
/ `bun.lock`, never gitignored. Python: apps pin exact via lockfile, libraries
lower-bound (STK-PY-06 owns the split); T2 research additionally freezes the environment
next to results. Lockfile integrity in CI and provenance concerns are SEC-SUPPLY.

### DEV-DEPS-02 — Automated update PRs MUST be enabled at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

Renovate preferred (better grouping and automerge control), Dependabot acceptable.
Without automation, updates happen never, then all at once under CVE pressure — the
worst possible cadence. At T1/T2 enabling it is encouraged but not required; a T1 repo
that opts in inherits the same config defaults.

### DEV-DEPS-03 — Update flow MUST match the tier: auto-merge small, read majors

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

- **T1/T2** (where automation is enabled): patch + minor auto-merge, gated on green
  checks — never auto-merge into a repo with no gates at all.
- **T3+**: updates arrive as grouped weekly PRs (one review sitting, not a drip of
  twenty), still CI-gated.
- **Majors, every tier**: never auto-merged. Read the changelog/release notes first,
  check the breaking-changes section against actual usage, and say so in the PR
  (DEV-GIT-06 evidence: "changelog read; breaking change X doesn't apply because…").

### DEV-DEPS-04 — Adding a dependency is a decision, and SHOULD be decided against the checklist

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

In order: (1) can stdlib or an already-present dependency do this? (2) maintenance
signals — a release within the year, an issue tracker that isn't a graveyard,
more than one maintainer for anything load-bearing; (3) license compatible (gate
formalized by LEG-LICENSING at T4); (4) size/transitive weight proportionate to the
problem. For Python, STK-PY-07's canonical table answers most cases before the checklist
starts. Record non-obvious choices in a line of the PR description; hard-to-reverse ones
get an ADR (DEV-DOCS-03).

### DEV-DEPS-05 — Current-version facts MUST be looked up, never answered from memory

**Tiers**: all required — **Layer**: A (attestation)

"What's the latest X / current model id / today's pricing" is answered from the registry
(`pip index versions`, `npm view`), official docs, or the `/claude-api` skill — at time
of use (Constitution C8). Training-memory answers are stale by construction and poison
pins, cost estimates, and API params silently. Applies with full force to the agent
itself: an agent writing `dependencies = [...]` checks the registry first.

### DEV-DEPS-06 — Fast-moving tools SHOULD get a monthly fast-lane review

**Tiers**: all advisory — **Layer**: A (attestation)

AI SDKs, model ids, agent tooling, and anything else that ships breaking changes monthly
doesn't fit the normal cadence: once a month, `/evolve-standards` sweeps the fast-lane
list (per-project, noted in GOVERNANCE.md), checks current versions/models against
what's pinned, and files upgrade tasks. This is how `claude-*` model ids stay current
without a CVE forcing the issue.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `package.json` implies a committed JS lockfile (T2+) | exit 0 | DEV-DEPS-01 |
| 2 | attestation: lockfile discipline across ecosystems | explicit yes | DEV-DEPS-01 |
| 3 | Renovate/Dependabot config file present (T3+) | exit 0 | DEV-DEPS-02 |
| 4–7 | attestation checklist (one per rule) | explicit yes | DEV-DEPS-03…06 |

**Remediation:** missing JS lockfile → `npm install --package-lock-only` (or the
pnpm/yarn equivalent), commit it, remove any `.gitignore` line hiding it · no update
automation at T3 → add `renovate.json` from the worked example and enable the GitHub
app · major merged unread and now broken → revert forward, read the changelog, reapply
deliberately.

## Worked Example

House-default `renovate.json` for a T3 repo:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended", ":semanticCommits"],
  "schedule": ["before 8am on monday"],
  "packageRules": [
    { "groupName": "weekly non-major", "matchUpdateTypes": ["patch", "minor"] },
    { "matchUpdateTypes": ["major"], "automerge": false, "labels": ["major-review"] }
  ]
}
```

T1/T2 variant (automation opted in): add
`{ "matchUpdateTypes": ["patch", "minor"], "automerge": true }` — safe only because the
DEV-CI gates (hooks/CI) must be green before Renovate merges. A registry lookup done
right, before pinning:

```bash
pip index versions httpx        # current release, from PyPI, now
npm view zod version            # current release, from npm, now
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `.gitignore`-ing the lockfile ("noise") | Every install is a new environment; CI ≠ laptop | Commit it; the noise is the signal (DEV-DEPS-01) |
| Updating deps only when something breaks | Updates arrive in a panic, twenty majors deep | Renovate weekly groups (DEV-DEPS-02/03) |
| Auto-merging majors "because CI is green" | CI can't see behavioral/API breakage it has no test for | Majors: changelog first, always (DEV-DEPS-03) |
| Adding a dep for one function | Transitive weight, supply-chain surface, forever-maintenance | Stdlib/existing dep first (DEV-DEPS-04) |
| Pinning `claude-3-5-sonnet…` from memory | Model ids churn; stale id = runtime 404 or worse, silent downgrade | `/claude-api` lookup at time of use (DEV-DEPS-05) |
| One giant "update everything" PR quarterly | Unreviewable; one breakage blocks fifty upgrades | Grouped weekly, majors separate |

## References

- Renovate docs (`config:recommended`, packageRules, automerge) — the mechanism
  DEV-DEPS-02/03 standardize on; Dependabot as fallback.
- Constitution C8 — the no-memory-facts article DEV-DEPS-05 operationalizes.
- STK-PY-06/07 — Python pinning split and canonical-library table this doc defers to.
- SEC-SUPPLY — vulnerability scanning and provenance; the security half of the same coin.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
