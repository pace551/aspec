---
id: LEG-LICENSING
title: Licensing
family: LEG
version: 1.0.2
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
allowlist (MIT/BSD/Apache-2.0/ISC fine; copyleft flagged for a human decision), the user's
own public repos carry an explicit LICENSE file (MIT default), and bundled assets —
fonts, icons, images — are checked at T3+ for web-facing work. Advisory below T3 because
a private personal tool creates no distribution, and most license obligations attach at
distribution.

## Normative Rules

### LEG-LICENSING-01 — T4 CI MUST run a dependency license audit

**Tiers**: T1–T3 advisory · T4 required — **Layer**: G

Install the `templates/ci/_fragments/license-audit.yml` fragment: it runs the per-stack scanner
(`pip-licenses` for Python, `license-checker` for npm, `go-licenses` for Go, `cargo-deny`
for Rust) and fails on any license outside the allowlist. The audit runs on every dependency change, not
annually — the dangerous moment is adoption. Advisory below T4 because obligations bind
on distribution/commercial use, but running it early at T3 is cheap insurance against
ripping out a load-bearing dependency later.

### LEG-LICENSING-02 — Copyleft adoption MUST be a recorded human decision

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

Allowlist: MIT, BSD (2/3-clause), Apache-2.0, ISC — adopt freely. Copyleft (GPL, LGPL,
and especially AGPL, which triggers on network use) is not banned, but in a T4 product it
requires a human decision from the user *before* adoption, recorded in `GOVERNANCE.md`
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
stop and raise the copyleft decision to the user (LEG-LICENSING-02) · public repo without
LICENSE → add MIT (or chosen license) now; it applies prospectively · desktop-only font in
a web bundle → replace with an OFL equivalent.

## Worked Example

Python job, as composed in `templates/ci/python.yml`:

```yaml
license-audit:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.14"
    - name: Install
      run: python -m venv .venv && .venv/bin/pip install -e '.[dev]'
    - name: Dependency license audit
      run: |
        .venv/bin/pip install --quiet pip-licenses
        project=$(.venv/bin/python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['name'])")
        allow="MIT;BSD-2-Clause;BSD-3-Clause;Apache-2.0;ISC;PSF-2.0;MPL-2.0"
        allow+=";MIT License;BSD License;Apache Software License;ISC License (ISCL)"
        allow+=";Python Software Foundation License;Mozilla Public License 2.0 (MPL 2.0)"
        allow+=";Apache-2.0 OR BSD-2-Clause;Apache-2.0 OR BSD-3-Clause;Apache-2.0 OR MIT;MIT OR Apache-2.0"
        .venv/bin/pip-licenses --ignore-packages "$project" --format=json --output-file=licenses.json
        .venv/bin/python - "$allow" <<'PY'
        import json, sys
        allow = {name.lower() for name in sys.argv[1].split(";")}
        bad = [p for p in json.load(open("licenses.json"))
               if not all(lic.strip().lower() in allow for lic in p["License"].split("; "))]
        for p in bad:
            print(f"license not allowed: {p['Name']} {p['Version']}: {p['License']}", file=sys.stderr)
        sys.exit(1 if bad else 0)
        PY
```

Why it is shaped this way, so it fails closed:

- **Allowlist, not denylist.** `--fail-on "GPL;…"` passes every license nobody thought to
  list (`CC-BY-NC-4.0`, `SSPL`, a custom EULA).
- **Every declared license must be allowed.** pip-licenses' own `--allow-only` passes a
  package when *any one* of its classifiers is allowed, so `BSD License` + `LGPLv3`
  would pass; the inline check requires all of them.
- **Exact matching.** PEP 639 packages report SPDX expressions; `--partial-match` would
  accept `MIT AND CC-BY-NC-4.0` because it contains `MIT`. Expressions pass only when
  listed verbatim, so the list carries the SPDX ids, their classifier names, and the
  common `OR` pairings of allowed licenses. An unlisted `OR` fails until reviewed.
- **The project itself is skipped** (`--ignore-packages`), since a fresh project may not
  declare a license yet; its dependencies are still audited.

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
| A license gate that fails open: a denylist, an any-classifier match, or substring matching | The licenses nobody listed, the second classifier, and `MIT AND …` all pass silently | Allowlist with exact matching where every declared license must be allowed (Worked Example) |
| Treating npm `license` field as ground truth | Metadata lies; transitive deps differ | Scanner over the installed tree |
| Bundling a "free" font into a web app | Free-for-desktop ≠ web embedding rights | Check terms; prefer OFL (LEG-LICENSING-04) |
| Claude Code silently swapping in a copyleft dep | Liability decision made by an agent | Flag and stop for the user (LEG-LICENSING-02) |

## References

- SPDX license list — canonical identifiers the allowlist and scanners use.
- choosealicense.com — the MIT-default rationale for LEG-LICENSING-03.
- pip-licenses / license-checker / go-licenses docs — the per-stack scanners behind the
  CI fragment.
- SIL Open Font License (OFL) — the known-clean font license class for LEG-LICENSING-04.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
- **1.0.1** (2026-10-06) — Replaced personal name references with generic "the user" wording for public release. No rule changes.
- **1.0.2** (2026-10-29) — Worked Example replaced with the `templates/ci/python.yml`
  job: the old `--fail-on` denylist passed any license it didn't name and audited the
  project's own unlicensed package. Adds a fail-open anti-pattern row and names
  `cargo-deny` as the Rust scanner. No rule changes.
