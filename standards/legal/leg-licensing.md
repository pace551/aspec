---
id: LEG-LICENSING
title: Licensing
family: LEG
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - license
  - licensing
  - gpl
  - agpl
  - copyleft
  - open source
  - dependency audit
  - font
  - icon
  - asset
requires: []
verification:
  - cmd: "sh -c 'grep -rqE \"license-audit\" .github/workflows/'"
    expect: "exit 0 — a license-audit job exists in CI (composed from the fragment)"
    layer: G
    rules: [LEG-LICENSING-01]
    tiers: [T4]
  - cmd: "attest: no copyleft (GPL/AGPL) dependency was adopted without an explicit recorded human decision"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-LICENSING-02]
  - cmd: "attest: if this repo is public, it has an explicit LICENSE file"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-LICENSING-03]
  - cmd: "attest: bundled assets (fonts, icons, images) have license terms permitting this use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-LICENSING-04]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Licensing (LEG-LICENSING)

## Abstract

Retires the risk of shipping a product whose dependencies or assets carry obligations
nobody read. Compliance in one breath: T4 CI runs a dependency license audit against an
allowlist (MIT/BSD/Apache-2.0/ISC fine; copyleft flagged for a human decision), James's
own public repos carry an explicit LICENSE file (MIT default), and bundled assets —
fonts, icons, images — are checked at T3+ for web-facing work. Advisory below T3 because
a private personal tool creates no distribution, and most license obligations attach at
distribution.

## Normative Rules

### LEG-LICENSING-01 — T4 CI MUST run a dependency license audit

**Tiers**: T1–T3 advisory · T4 required — **Layer**: G

Install the `templates/ci/_fragments/license-audit.yml` fragment: it runs the per-stack scanner
(`pip-licenses` for Python, `license-checker` for npm, `go-licenses` for Go) and fails on
any license outside the allowlist. The audit runs on every dependency change, not
annually — the dangerous moment is adoption. Advisory below T4 because obligations bind
on distribution/commercial use, but running it early at T3 is cheap insurance against
ripping out a load-bearing dependency later.

### LEG-LICENSING-02 — Copyleft adoption MUST be a recorded human decision

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

Allowlist: MIT, BSD (2/3-clause), Apache-2.0, ISC — adopt freely. Copyleft (GPL, LGPL,
and especially AGPL, which triggers on network use) is not banned, but in a T4 product it
requires a human decision from James *before* adoption, recorded in `GOVERNANCE.md`
(dependency, license, why the obligation is acceptable). Unknown/custom licenses get the
same treatment. Claude Code never resolves this alone: flag and stop — this is a
liability call, not an engineering call.

### LEG-LICENSING-03 — Public repos MUST carry an explicit LICENSE file

**Tiers**: all required — **Layer**: A (attestation)

Applies only to repos published publicly (private repos attest trivially). No LICENSE
means all-rights-reserved by default, which is the opposite of what publishing intends.
House default is MIT, applied at scaffold time by `DEV-BOOTSTRAP`; choosing anything else
is fine but deliberate. Published packages (the `tiers.md` carve-out) additionally declare
the license in package metadata (`pyproject.toml` `license`, `package.json` `license`) so
downstream audits like LEG-LICENSING-01 see it.

### LEG-LICENSING-04 — Bundled asset licenses MUST be checked at T3+ for web work

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Fonts, icon sets, images, and audio shipped with a web-facing product have licenses too,
and scanners don't see them. Before bundling: confirm the license permits web
embedding/redistribution (many "free" fonts are free for *desktop* use only; icon sets
often require attribution), satisfy any attribution requirement, and note
source + license per asset in the project `CLAUDE.md` or an `ASSETS.md`. Prefer
known-clean sources: OFL fonts (Google Fonts), MIT/ISC icon sets.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `grep -rqE "license-audit" .github/workflows/` (T4) | license-audit job present in CI | LEG-LICENSING-01 |
| 2 | attest: no unreviewed copyleft adoption | explicit yes | LEG-LICENSING-02 |
| 3 | attest: LICENSE file present if public | explicit yes | LEG-LICENSING-03 |
| 4 | attest: bundled asset licenses checked (T3+) | explicit yes | LEG-LICENSING-04 |

**Remediation:** audit fails on a new dependency → swap for an allowlisted alternative, or
stop and raise the copyleft decision to James (LEG-LICENSING-02) · public repo without
LICENSE → add MIT (or chosen license) now; it applies prospectively · desktop-only font in
a web bundle → replace with an OFL equivalent.

## Worked Example

Python job from the `templates/ci/_fragments/license-audit.yml` fragment:

```yaml
license-audit:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: |
        python3 -m venv .venv && .venv/bin/pip install -q -e . pip-licenses
        .venv/bin/pip-licenses --fail-on="GPL;GPLv2;GPLv3;LGPL;AGPLv3;Unknown" \
          --format=markdown --output-file=license-report.md
    - uses: actions/upload-artifact@v4
      with: {name: license-report, path: license-report.md}
```

A GOVERNANCE.md record of a conscious copyleft decision:

```yaml
license_decisions:
  - dependency: some-agpl-tool
    license: AGPL-3.0
    decision: rejected 2026-07-22 — network copyleft incompatible with closed T4 product;
      replaced with mit-alternative
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Annual license review instead of CI | Obligation adopted in March, discovered in January | Audit on every dependency change (LEG-LICENSING-01) |
| "GPL is banned" as a blanket rule | Overcorrection; sometimes the obligation is fine | Human decision per case, recorded (LEG-LICENSING-02) |
| Public repo with no LICENSE "so it's free" | Default is all-rights-reserved — nobody can legally use it | Explicit MIT via DEV-BOOTSTRAP (LEG-LICENSING-03) |
| Treating npm `license` field as ground truth | Metadata lies; transitive deps differ | Scanner over the installed tree |
| Bundling a "free" font into a web app | Free-for-desktop ≠ web embedding rights | Check terms; prefer OFL (LEG-LICENSING-04) |
| Claude Code silently swapping in a copyleft dep | Liability decision made by an agent | Flag and stop for James (LEG-LICENSING-02) |

## References

- SPDX license list — canonical identifiers the allowlist and scanners use.
- choosealicense.com — the MIT-default rationale for LEG-LICENSING-03.
- pip-licenses / license-checker / go-licenses docs — the per-stack scanners behind the
  CI fragment.
- SIL Open Font License (OFL) — the known-clean font license class for LEG-LICENSING-04.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
