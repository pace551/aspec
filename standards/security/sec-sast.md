---
id: SEC-SAST
title: Static Application Security Testing
family: SEC
version: 1.0.4
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
published: required
stacks: all
triggers:
  - sast
  - static analysis
  - bandit
  - semgrep
  - gosec
  - clippy
  - eslint security
  - security scan
  - code scanning
requires: []
verification:
  - cmd: "bash \"$GOVERNANCE_DIR/checks/sec-sast.sh\""
    expect: "exit 0 — stack scanner clean (missing scanner degrades to a documented warning at T1/T2)"
    layer: G
    rules: [SEC-SAST-01]
    tiers: [T1, T2]
  - cmd: "bash \"$GOVERNANCE_DIR/checks/sec-sast.sh\" --tier T3"
    expect: "exit 0 — stack scanner clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-SAST-01]
    tiers: [T3]
  - cmd: "bash \"$GOVERNANCE_DIR/checks/sec-sast.sh\" --tier T4"
    expect: "exit 0 — stack scanner clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-SAST-01]
    tiers: [T4]
  - cmd: "attest: the SAST job from templates/ci/_fragments/sast.yml (or equivalent) runs in this project's CI, and its findings block a merge (the job fails on them, or a branch rule requires code scanning results)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SAST-02]
    tiers: [T3, T4]
  - cmd: "attest: every suppressed SAST finding has an inline justification; no blanket disables were added"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SAST-03]
  - cmd: "attest: semgrep was considered as the cross-stack second opinion (adopted or consciously skipped)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SAST-04]
last_review: 2026-11-06
---

# Static Application Security Testing (SEC-SAST)

## Abstract

Machine review for the vulnerability classes machines catch reliably: string-built SQL,
`shell=True`, weak hashes, tainted flows. Each stack has one required scanner (bandit /
semgrep+eslint security plugins / gosec+go vet / clippy) run by
`checks/sec-sast.sh`, which detects the project type and degrades with a documented
warning when a scanner is missing at T1/T2 — and fails at T3+, where the gate may not
silently disappear. Findings are fixed or suppressed individually with a written reason;
blanket disables are the canonical violation. At T3+ the scan also runs in CI via the
shared fragment. Dependency CVEs are SEC-SUPPLY's job, not this one's.

## Normative Rules

### SEC-SAST-01 — The stack's required SAST scanner MUST pass

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

| Stack | Required scanner | Command | Notes |
|---|---|---|---|
| python | bandit | `.venv/bin/bandit -r src -q` (script collection: `-c pyproject.toml -r . -q`) | config and justified skips per STK-PY-04 |
| typescript | eslint security plugins + semgrep | `semgrep scan --config p/security-audit` | `eslint-plugin-security` (+ typescript-eslint) live in the project's own lint config; semgrep is the runnable gate |
| go | go vet + gosec | `go vet ./... && gosec ./...` | vet is the floor, gosec the security pass |
| rust | clippy | `cargo clippy -- -D warnings` | `cargo audit` is SEC-SUPPLY-01, not SAST — the boundary is code analysis here, dependency CVEs there |
| swift | CodeQL, in CI | `templates/ci/swiftui.yml`'s `sast` job; `sec-sast.sh` checks that a job in the repository's workflows runs CodeQL on Swift, isn't switched off (`if: false`, or a workflow run only by hand), and sends its results somewhere (uploaded to code scanning, or named by a later step); that its findings then block a merge is SEC-SAST-02's attestation, since no reading of a workflow can settle it. CodeQL's default setup leaves no workflow to check: use the job | no Swift SAST scanner is free to run locally on private code: CodeQL's CLI license excludes it and semgrep's free engine finds little in Swift. CodeQL is free on public repos; private ones need GitHub Advanced Security |

`checks/sec-sast.sh` selects by manifest (`pyproject.toml`/`package.json`/`go.mod`/
`Cargo.toml`, and `Package.swift`, an Xcode project or a workspace for Swift) and runs everything that
matches. Degradation contract: missing scanner at
T1/T2 → documented warning, pass (this fallback is explicitly sanctioned); at T3/T4
(`--tier T3|T4`) → clear message, exit 1. Fresh scaffolds with nothing to scan pass at
T1/T2 and fail at T3+ by design.

### SEC-SAST-02 — SAST MUST run in CI at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Local runs rot the moment they become optional. T3+ projects include the shared job
fragment `templates/ci/_fragments/sast.yml` (maintained by the CI-templates workstream)
in their workflow — or an equivalent job invoking `sec-sast.sh --tier T3` — so every PR
is scanned, not just the ones where someone remembered. The CI image installs the
required scanner; "not installed on the runner" is a build failure, not a skip. A finding
must block the merge, as a failing `sec-sast.sh` would (SEC-SAST-01): either the job
fails on it, or (for results uploaded to GitHub code scanning, as CodeQL does by
default) a branch rule requires code scanning results. That rule is a repository setting
the checkout can't show, which is why this rule is attested.

### SEC-SAST-03 — Findings MUST be fixed or suppressed individually with a written justification

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Suppression is per-finding and inline — `# nosec <id> — reason`,
`// eslint-disable-next-line security/x — reason`, `# nosemgrep: rule — reason`,
`#[allow(clippy::x)] // reason` — never a config-level severity downgrade, blanket
`ignore` list, or `--exit-zero` added to make CI green. Injection and crypto findings
(bandit B608/B602/B324 and their analogues) are fixed, never suppressed — the same line
STK-PY-04 draws. A suppression without a reason is a violation even if the finding is a
true false-positive.

### SEC-SAST-04 — semgrep SHOULD be the cross-stack second opinion

**Tiers**: all advisory — **Layer**: A (attestation)

One tool that reads every language in the house, with `p/security-audit` as the
baseline ruleset. Its real value is custom rules: when a repo develops a house
anti-pattern (the third time an agent writes `yaml.load`, a datetime without tzinfo, an
unparameterized query the primary scanner missed), encode it once in `.semgrep.yml` and
it is enforced forever. Adopt or consciously skip — the attestation asks only that the
choice was made, not that the answer is yes.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash "$GOVERNANCE_DIR/checks/sec-sast.sh"` (T1/T2) | exit 0 — clean, or documented missing-scanner warning | SEC-SAST-01 |
| 2 | `… sec-sast.sh --tier T3` (T3) | exit 0 — clean; missing scanner fails | SEC-SAST-01 |
| 3 | `… sec-sast.sh --tier T4` (T4) | exit 0 — clean; missing scanner fails | SEC-SAST-01 |
| 4 | attest: CI runs the sast.yml fragment (T3+), and its findings block a merge | explicit yes recorded | SEC-SAST-02 |
| 5 | attest: suppressions individually justified | explicit yes recorded | SEC-SAST-03 |
| 6 | attest: semgrep considered | explicit yes recorded | SEC-SAST-04 |

**Remediation:** bandit B608 → parameterized queries (SEC-INPUT-02) · B602/B604 →
`shell=False` + argument list (SEC-INPUT-03) · B324 → SHA-256+ (SEC-CRYPTO-02) · scanner
missing at T3+ → install it in `[dev]` extras / CI image, don't lower the tier flag ·
semgrep registry unreachable offline → rerun with network; don't pin `--config` to
nothing.

## Worked Example

A Python T3 project. `pyproject.toml` carries the scanner in dev extras (per STK-PY):

```toml
[project.optional-dependencies]
dev = ["pytest>=7", "ruff>=0.4", "bandit>=1.7", "pip-audit>=2.6"]
```

Local gate and what passing looks like:

```
$ bash "$GOVERNANCE_DIR/checks/sec-sast.sh" --tier T3
sec-sast: running: .venv/bin/bandit -r src -q
sec-sast: clean
```

CI: copy the job from `templates/ci/_fragments/sast.yml` into
`.github/workflows/ci.yml` next to the lint/test jobs. A justified suppression, the
only sanctioned kind:

```python
subprocess.run(["osascript", "-e", FIXED_SCRIPT])  # nosec B603 — argv list, constant script, no user input
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Adding `--exit-zero` / `\|\| true` to a red scan | Converts the gate into decoration | Fix or justify per finding (SEC-SAST-03) |
| Config-level `skips = ["B608", "B602"]` to pass CI | Permanently blinds the scanner to injection | Inline `# nosec` with reason; injection findings get fixed |
| SAST only on the laptop, never in CI (T3+) | The one unscanned PR is the vulnerable one | Wire the fragment (SEC-SAST-02) |
| Treating clippy as style noise, building with warnings | Security-relevant lints drown with the cosmetic ones | `-D warnings`; allow specific lints with reasons |
| eslint without security plugins counted as SAST | Default eslint checks style, not taint | `eslint-plugin-security` + semgrep per the table |
| Running SAST on generated/vendored code and triaging forever | Noise teaches everyone to ignore red | Scope to `src/` (the table's commands already do) |

## References

- bandit documentation — Python scanner and test-ID vocabulary (B6xx) the remediation
  map uses.
- semgrep registry, `p/security-audit` — the chosen cross-stack baseline ruleset;
  custom-rule syntax for house patterns.
- gosec + `go vet` docs — the Go pairing; vet ships with the toolchain so the floor is
  always installable.
- rust-clippy lint index — why `-D warnings` is the gate posture rather than default
  warn.
- OWASP Source Code Analysis Tools page — the honest framing of what SAST can and
  cannot catch, which is why SEC-INPUT/SEC-CRYPTO still exist.

## Changelog

- **1.0.4** (2026-11-06) — Per-stack table: Swift (`templates/ci/swiftui.yml`). Its SAST is CodeQL in CI, because no Swift scanner is free to run locally on private code; `sec-sast.sh` now recognizes Swift projects and checks that a workflow job runs CodeQL on Swift instead of failing them as "no recognized manifest" at T3+; a job whose results go nowhere (kept, and neither sent on nor mentioned by a later step) doesn't count. SEC-SAST-02's attestation now spells out that findings must block a merge (a failing job, or a branch rule requiring code scanning results), which SEC-SAST-01's "MUST pass" already required of an equivalent job. No new requirements.
- **1.0.3** (2026-11-04) — Per-stack table: Python script collections (STK-PY-01) run bandit over the repo with `[tool.bandit]` exclusions instead of `src/`, matching STK-PY-04 and `sec-sast.sh`. No rule changes.
- **1.0.2** (2026-11-04) — Adds `published: required` (ADR-0005): its risk ships with the package, so published packages apply it at T3 weight. No change for projects that aren't published packages.
- **1.0.1** (2026-10-27) — Portability: framework check scripts referenced via `$GOVERNANCE_DIR` (exported by run-verification.py) instead of a hardcoded home-directory path.
- **1.0.0** (2026-07-22) — Initial version.
