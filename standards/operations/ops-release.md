---
id: OPS-RELEASE
title: Versioning & Release
family: OPS
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - release
  - version
  - semver
  - changelog
  - tag
  - conventional commits
  - release-please
  - publish
  - artifact
requires: []
verification:
  - cmd: "sh -c '[ -f CHANGELOG.md ]'"
    expect: "exit 0 — CHANGELOG.md exists at the repo root"
    layer: G
    rules: [OPS-RELEASE-03]
    tiers: [T3, T4]
  - cmd: "attest: anything consumed by others is versioned semver and breaking changes bumped major"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-RELEASE-01]
  - cmd: "attest: releases are cut by automation from conventional commits (t3+) or deliberate milestone tags (t1/t2)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-RELEASE-02]
    tiers: [T2, T3, T4]
  - cmd: "attest: changelog.md is written for humans — features/fixes/breaking, not commit-log noise"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-RELEASE-03]
    tiers: [T3, T4]
  - cmd: "attest: no release was cut from a dirty tree or unpushed commit"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-RELEASE-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: every published artifact is traceable to the exact git sha that produced it"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-RELEASE-05]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Versioning & Release (OPS-RELEASE)

## Abstract

Answers "what version is this, what changed, and which commit built it" without
archaeology. Compliance in one breath: anything others consume carries semver;
T3+ releases are cut by automation (conventional commits → release-please/git-cliff →
changelog + tag), never from a dirty tree; `CHANGELOG.md` speaks to humans; every
artifact traces to a SHA. T1/T2 discount: no release machinery — a git tag at a
meaningful milestone is the whole ceremony. Builds on C4 (conventional commits are
already constitutional); deploy mechanics live in `OPS-DEPLOY`.

## Normative Rules

### OPS-RELEASE-01 — Anything consumed by others MUST use semver

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Libraries, packages, CLIs others install, and public APIs version `MAJOR.MINOR.PATCH`:
breaking → major, feature → minor, fix → patch. Pre-1.0 is honest about instability but
still never breaks in a patch. Published libraries get this at T3 weight regardless of
tier (tiers.md carve-out). Internal-only T1 tools MAY skip versioning entirely — a tag
when something is worth returning to is enough.

### OPS-RELEASE-02 — T3+ releases MUST be automated from conventional commits; T1/T2 milestone tags suffice

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

C4 already mandates conventional commits; at T3+ they become machine input:
release-please (default; native GitHub Actions flow) or git-cliff computes the version
bump, writes the changelog entry, and cuts the tag + GitHub Release. Humans decide *when*
to release (merging the release PR); the mechanics are never hand-run. At T1/T2 the
discount is explicit: `git tag -a v0.3 -m "first end-to-end run"` at meaningful
milestones, no tooling required.

### OPS-RELEASE-03 — CHANGELOG.md MUST exist and speak to humans

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G + A

Keep-a-Changelog shape: newest first, grouped Added/Changed/Fixed/Removed, breaking
changes flagged loudly at the top of the entry. Generated entries (release-please) are
acceptable as the base but get a human pass when the release contains anything a user
must *do* (migration steps, config changes). A raw `git log` dump is not a changelog —
it answers "what commits", not "what does this mean for me".

### OPS-RELEASE-04 — Releases MUST NOT be cut from a dirty tree

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

A release/tag is only cut from a clean, committed, pushed state — never with uncommitted
changes, stashed hacks, or local-only commits, because the tag would then name a state
that exists nowhere else. CI-cut releases (OPS-RELEASE-02) satisfy this structurally; the
rule bites on manual T1/T2 tags: `git status --porcelain` empty before tagging. T2
research runs inherit this: a result is only citable if produced from a committed SHA
(reproducibility, `TST-FIXTURES`).

### OPS-RELEASE-05 — Every artifact MUST be traceable to the SHA that produced it

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Container images tagged with the SHA (plus a moving semver tag), packages carrying
version metadata that maps to a tag, Lambda bundles labelled in description or env.
Given any running or published artifact, `git checkout <sha>` must reproduce its source
in one step — this is the release-side half of `OPS-DEPLOY-05`'s "SHA in /health", and
what makes incident bisection (`OPS-INCIDENT`) possible.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `[ -f CHANGELOG.md ]` (T3+) | file exists | OPS-RELEASE-03 |
| 2 | attestation — semver for consumed things | explicit yes recorded | OPS-RELEASE-01 |
| 3-6 | attestation checklist (tier-scoped) | explicit yes recorded | OPS-RELEASE-02…05 |

**Remediation:** no CHANGELOG.md at T3 → adopt release-please, which creates and
maintains it · breaking change shipped as minor → bump major now, note in changelog ·
tag cut from dirty tree → delete tag, commit/push, re-tag the real state · image tagged
only `latest` → add SHA tag to the build step.

## Worked Example

T3 release automation — `.github/workflows/release.yml`:

```yaml
name: release
on:
  push: { branches: [main] }
permissions: { contents: write, pull-requests: write }
jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with: { release-type: python }   # maintains CHANGELOG.md, version, tag, release
```

Flow: conventional commits merge to `main` → release-please maintains a release PR
(version bump + changelog diff) → merging that PR cuts the tag and GitHub Release →
the deploy workflow (`OPS-DEPLOY`) picks up the tag and ships an image tagged
`v1.4.0` + `sha-3f2a91c`.

T1 milestone, complete ceremony:

```bash
git status --porcelain   # must be empty (OPS-RELEASE-04)
git tag -a v0.2 -m "scheduler survives reboot"
git push --tags
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Hand-editing version strings and tags at T3 | Drift between tag, code, changelog | release-please owns all three (OPS-RELEASE-02) |
| `CHANGELOG.md` = pasted `git log --oneline` | Answers nothing a user asks | Human-meaning entries, Keep-a-Changelog (OPS-RELEASE-03) |
| Breaking API change in a patch release | Consumers auto-update into breakage | Major bump + loud changelog flag (OPS-RELEASE-01) |
| Tagging with uncommitted "one last fix" in the tree | Tag names a state that exists only on one laptop | Clean tree, pushed, then tag (OPS-RELEASE-04) |
| Only `latest` image tag in ECR | Cannot tell what is deployed or roll back to a known state | SHA tag + semver tag per image (OPS-RELEASE-05) |
| Version bump commits without conventional prefixes | Breaks the automation that reads them | C4 conventional commits, enforced by hook |

## References

- semver.org (Semantic Versioning 2.0.0) — the contract OPS-RELEASE-01 encodes.
- keepachangelog.com — the human-facing changelog format for OPS-RELEASE-03.
- release-please docs (googleapis/release-please-action) — the default T3+ automation.
- git-cliff docs — sanctioned alternative when a release PR flow doesn't fit.
- Conventional Commits spec — the commit grammar (via C4) the automation consumes.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
