---
id: SEC-SUPPLY
title: Supply Chain Security
family: SEC
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
  - supply chain
  - lockfile
  - pip-audit
  - npm audit
  - cargo audit
  - osv
  - github actions
  - new package
  - install script
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sca.sh"
    expect: "exit 0 — dependency audit clean (missing scanner degrades to a documented warning at T1/T2)"
    layer: G
    rules: [SEC-SUPPLY-01]
    tiers: [T1, T2]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sca.sh --tier T3"
    expect: "exit 0 — dependency audit clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-SUPPLY-01]
    tiers: [T3]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sca.sh --tier T4"
    expect: "exit 0 — dependency audit clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-SUPPLY-01]
    tiers: [T4]
  - cmd: "attest: every dependency manifest has its lockfile committed (applications) and installs are reproducible from it"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SUPPLY-02]
  - cmd: "attest: all GitHub Actions in workflows are pinned to a full commit SHA with a version comment"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SUPPLY-03]
    tiers: [T3, T4]
  - cmd: "attest: version pinning follows the app/library split (apps exact via lockfile, libraries lower-bounded)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SUPPLY-04]
  - cmd: "attest: no unverified curl-pipe-to-shell installs were run; new dependencies passed the provenance sniff test"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SUPPLY-05]
last_review: 2026-07-22
---

# Supply Chain Security (SEC-SUPPLY)

## Abstract

Your dependencies, their dependencies, and your CI's actions are all code you run with
your credentials. This standard keeps that surface governed: a per-stack SCA scanner
(pip-audit / npm audit / govulncheck / cargo-audit, run by `checks/sec-sca.sh`) must be
clean or per-CVE waived; lockfiles are committed so installs are reproducible; GitHub
Actions are SHA-pinned at T3+; and new dependencies and install methods pass a one-minute
provenance sniff test — no `curl | bash` without a checksum, no typosquat-shaped names.
Static analysis of your own code is SEC-SAST; this standard governs everything you didn't
write.

## Normative Rules

### SEC-SUPPLY-01 — Dependency audits MUST be clean, or findings waived per-CVE

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

| Stack | Scanner | Fallback |
|---|---|---|
| python | `.venv/bin/pip-audit` | — |
| typescript | `npm audit --audit-level=high` (needs `package-lock.json`) | `osv-scanner -r .` for pnpm/yarn/bun lockfiles |
| go | `govulncheck ./...` (call-graph aware: flags reachable vulns only) | `osv-scanner -r .` |
| rust | `cargo audit` | — |

`checks/sec-sca.sh` runs the right one by manifest, lenient at T1/T2 (missing scanner →
documented warning), strict at T3+ (`--tier T3|T4` → missing scanner fails). A finding
is fixed by upgrade or waived per-CVE in `GOVERNANCE.md` with a reachability argument
and an expiry — mirroring STK-PY-05; never a standing ignore. Audit cadence between
releases is `DEV-DEPS`'s job.

### SEC-SUPPLY-02 — Applications MUST commit lockfiles; installs are reproducible from them

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Every manifest ships its lock: `package-lock.json` (or `pnpm-lock.yaml`/`yarn.lock`),
`uv.lock` or `==`-pinned `requirements.txt` export, `Cargo.lock`, `go.sum`. CI and
deploys install from the lockfile (`npm ci`, `uv sync`), never from loose ranges — an
unlocked install is a supply-chain roll of the dice on every build, and it also breaks
T2 reproducibility (STK-PY-06's freeze requirement is this rule's Python face).
Libraries MAY omit application lockfiles from what they publish, but the repo itself
still commits one so its own CI is deterministic.

### SEC-SUPPLY-03 — GitHub Actions MUST be pinned to a full commit SHA at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4.1.7` — never
`@v4`, never `@main`. Tags are mutable: the tj-actions/changed-files compromise (2025)
retagged existing releases to exfiltrate CI secrets from every workflow that trusted a
tag. The trailing version comment keeps pins human-readable, and Dependabot understands
and updates SHA pins. Local reusable workflows (`./.github/workflows/…`) are exempt —
they ride the repo's own history.

### SEC-SUPPLY-04 — Version pinning SHOULD follow the app/library split

**Tiers**: all advisory — **Layer**: A (attestation)

Applications pin exact versions (via the lockfile above); libraries declare lower
bounds plus known-bad exclusions so consumers can resolve. Upgrades are deliberate
diffs — reviewed lockfile changes with the changelog skimmed — not side effects of an
unpinned install. The full cadence/auto-update policy (Dependabot config, upgrade
batching) lives in `DEV-DEPS`; this rule only fixes the direction: apps exact, libs
bounded.

### SEC-SUPPLY-05 — Installs and new dependencies MUST pass a provenance sniff test

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

No `curl | bash` (or `iwr | iex`) without a pinned version and checksum verification —
download, verify `shasum -a 256 -c`, then run; prefer brew or the ecosystem's official
package manager, which do this for you. Before adding a dependency: read the exact name character-by-character
(typosquats live one transposition away — `requests` vs `request`), check the source
repo exists and is maintained, prefer the ecosystem's well-known choice
(STK-PY-07's canonical table) over a 40-star lookalike, and be suspicious of packages
with install-time scripts. One minute of vigilance per new dep, not a review board.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/sec-sca.sh` (T1/T2) | exit 0 — clean or documented warning | SEC-SUPPLY-01 |
| 2 | `… sec-sca.sh --tier T3` (T3) | exit 0 — clean; missing scanner fails | SEC-SUPPLY-01 |
| 3 | `… sec-sca.sh --tier T4` (T4) | exit 0 — clean; missing scanner fails | SEC-SUPPLY-01 |
| 4 | attest: lockfiles committed, installs reproducible | explicit yes recorded | SEC-SUPPLY-02 |
| 5 | attest: Actions SHA-pinned (T3+) | explicit yes recorded | SEC-SUPPLY-03 |
| 6 | attest: app/lib pinning split honored | explicit yes recorded | SEC-SUPPLY-04 |
| 7 | attest: provenance sniff test on installs/new deps | explicit yes recorded | SEC-SUPPLY-05 |

**Remediation:** audit finding → upgrade first; unreachable-CVE waiver `{rule_id:
SEC-SUPPLY-01, reason, expires}` in GOVERNANCE.md only when upgrade is genuinely blocked ·
`npm audit` errors without a lockfile → commit `package-lock.json` (that's SEC-SUPPLY-02
failing loudly) · tag-pinned action → replace with the tag's current SHA + comment ·
`curl | bash` in a README you're following → download the versioned artifact and verify
its published checksum instead.

## Worked Example

SHA-pinned workflow step and a compliant one-off installer:

```yaml
# .github/workflows/ci.yml
- uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4.1.7
- uses: actions/setup-python@39cd14951b08e74b54015e9e001cdefcf80e669f # v5.1.1
```

```bash
# Instead of: curl -fsSL https://example.dev/install.sh | bash
curl -fsSLO https://example.dev/releases/v1.4.2/tool-v1.4.2-darwin-arm64.tar.gz
echo "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08  tool-v1.4.2-darwin-arm64.tar.gz" \
  | shasum -a 256 -c   # checksum from the project's release page
tar -xzf tool-v1.4.2-darwin-arm64.tar.gz
```

A per-CVE waiver, the only sanctioned shape for a lingering finding:

```yaml
# GOVERNANCE.md → waivers
- rule_id: SEC-SUPPLY-01
  reason: "GHSA-xxxx-yyyy in transitive dev-only dep 'foo'; not in runtime path; fix blocked on upstream major"
  expires: 2026-09-30
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `npm audit fix --force` to silence CI | Blind major upgrades; trades a known CVE for unknown breakage | Targeted upgrade per finding, read the diff |
| Standing "ignore vulnerabilities" config | The one real RCE arrives during the ignore window | Per-CVE waiver with expiry (SEC-SUPPLY-01) |
| `uses: some-action@main` | You run whatever that repo's main is at trigger time | Full SHA + version comment (SEC-SUPPLY-03) |
| Lockfile in `.gitignore` "to avoid merge conflicts" | Every environment resolves differently; CI ≠ laptop ≠ prod | Commit it; conflicts are cheaper than drift |
| `curl \| bash` from a README | Executes unauthenticated remote code as you, uncached and unauditable | Versioned artifact + checksum (SEC-SUPPLY-05) |
| Adding a dep for a 5-line function | Every dep is an audit surface and a typosquat target forever | Write the function; cite STK-PY-07 before adding |

## References

- OSV.dev / osv-scanner — the shared vulnerability database behind pip-audit and the
  cross-ecosystem fallback in `sec-sca.sh`.
- GitHub, "Security hardening for GitHub Actions" — the source of the SHA-pinning
  guidance in SEC-SUPPLY-03.
- tj-actions/changed-files incident write-ups (March 2025) — the concrete retagged-
  action compromise that makes tag pins indefensible at T3+.
- govulncheck documentation — reachability analysis, why Go findings are low-noise.
- SLSA framework — vocabulary for provenance levels; SEC-SUPPLY-05 is an informal
  personal-scale slice of it.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
