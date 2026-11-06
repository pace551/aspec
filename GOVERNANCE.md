# Governance Manifest

```yaml
tier: T1
classified: 2026-11-05
tier_override: null
published_package: true
stacks: [python]
standards:
  - {id: AI-SECURITY, version: 1.0.1}
  - {id: DEV-BOOTSTRAP, version: 1.0.4}
  - {id: DEV-CI, version: 1.0.3}
  - {id: DEV-DEPS, version: 1.0.1}
  - {id: DEV-GIT, version: 1.0.3}
  - {id: DEV-REVIEW, version: 1.0.1}
  - {id: LEG-LICENSING, version: 1.0.4}
  - {id: OPS-FINOPS, version: 1.0.0}
  - {id: OPS-RELEASE, version: 1.0.0}
  - {id: SEC-CRYPTO, version: 1.0.2}
  - {id: SEC-INPUT, version: 1.0.2}
  - {id: SEC-SAST, version: 1.0.4}
  - {id: SEC-SECRETS, version: 1.0.3}
  - {id: SEC-SUPPLY, version: 1.0.3}
  - {id: STK-PY, version: 1.0.5}
  - {id: TST-FIXTURES, version: 1.0.2}
  - {id: TST-POLICY, version: 1.0.1}
  - {id: TST-RATCHET, version: 1.0.5}
  - {id: TST-VERIFY, version: 1.0.1}
waivers: []
external_action_approvals:
  - {action: "push branches and open pull requests on github.com/pace551/aspec", granted: 2026-10-28}
pii_inventory: n/a
last_verified: 2026-11-05
attestations:
  - {rule_id: AI-SECURITY-01, followed: false, note: "not audited: skills and hooks haven't been reviewed for untrusted-content handling; no code here calls an LLM", date: 2026-11-03}
  - {rule_id: AI-SECURITY-02, followed: false, note: "not audited: the repo ships no agent tool set of its own; Claude Code permission settings live outside it", date: 2026-11-03}
  - {rule_id: AI-SECURITY-03, followed: true, note: "no code in checks/, hooks/ or scripts/ calls an LLM or executes model output (grep for API clients: none)", date: 2026-11-03}
  - {rule_id: AI-SECURITY-04, followed: true, note: "no secrets in the repo (secret-scan clean, CI gitleaks over full history); nothing relies on a hidden prompt", date: 2026-11-03}
  - {rule_id: DEV-BOOTSTRAP-08, followed: true, note: "public repo with BSL 1.1 LICENSE at the root", date: 2026-11-03}
  - {rule_id: DEV-GIT-02, followed: true, note: "each PR in this session (#13-#25) is one logical change in one commit", date: 2026-11-03}
  - {rule_id: DEV-GIT-07, followed: false, note: "8 commits from 2026-10-27 (e00173f..a36989d) carry a free-text 'Generated with [Devin]' line outside trailer form; main isn't rewritten; commits since use trailers only", date: 2026-11-03}
  - {rule_id: OPS-FINOPS-01, followed: true, note: "nothing that can bill is deployed; no AWS resources", date: 2026-11-03}
  - {rule_id: OPS-FINOPS-02, followed: true, note: "no LLM API use in this repo, so no spend to cap", date: 2026-11-03}
  - {rule_id: OPS-FINOPS-04, followed: true, note: "no billing projects; GitHub Actions on a public repo is free", date: 2026-11-03}
  - {rule_id: OPS-FINOPS-05, followed: true, note: "no infrastructure", date: 2026-11-03}
  - {rule_id: OPS-RELEASE-01, followed: true, note: "semver via release-please from conventional commits; unchanged by this PR, which only swaps the token it runs with", date: 2026-11-04}
  - {rule_id: SEC-SECRETS-03, followed: true, note: "one CI secret: the release GitHub App private key, held in GitHub Actions encrypted secrets (RELEASE_APP_PRIVATE_KEY) and never in a tracked file; no local credentials", date: 2026-11-04}
  - {rule_id: SEC-SECRETS-04, followed: true, note: "none observed this session; secret-scan and full-history gitleaks clean", date: 2026-11-03}
  - {rule_id: SEC-SECRETS-05, followed: true, note: "no secret known to have been exposed", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-01, followed: true, note: "test data is synthetic; the noncompliant-fixture's secrets are deliberate fakes (.gitleaksignore)", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-02, followed: true, note: "no randomness or wall-clock use in checks/test_*.py (grep); dates are passed explicitly; each test builds its own temp dir", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-03, followed: true, note: "no network libraries in tests (grep); git tests use local file:// remotes", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-04, followed: false, note: "only the tests added this session (release-prep, git-gate) were checked: they build per-test data; older tests not audited", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-05, followed: true, note: "no flaky test observed", date: 2026-11-03}
  - {rule_id: TST-POLICY-01, followed: true, note: "xargs fix began with failing tests: test_xargs_null.py (3 standards cmds passed a noncompliant spaced path, step-1 search found no spaced notes, lint missed -P0 and rejected -n 1 -0) and test_scan_spaced_paths.py (both scanners split spaced paths before their linters; then, per Devin, passed with exit 0 when find could not read a directory, and failed on an unreadable excluded dir)", date: 2026-11-05}
  - {rule_id: TST-POLICY-02, followed: true, note: "release-prep.py (#21) was written test-first", date: 2026-11-03}
  - {rule_id: TST-POLICY-03, followed: true, note: "scripts/*.sh are glue over existing gates; run directly, plus negative runs (Python 3.9 only, ruff violation)", date: 2026-11-03}
  - {rule_id: TST-POLICY-05, followed: true, note: "no coverage percentage gate anywhere in this repo's CI (grep)", date: 2026-11-03}
  - {rule_id: TST-VERIFY-01, followed: true, note: "lint (scripts/lint.sh), unit tests (scripts/test.sh), hooks on the real commit and push, then run-verification", date: 2026-11-03}
  - {rule_id: TST-VERIFY-02, followed: true, note: "release.yml App token exercised by its real run: release PR #39 opened as aspec-release[bot], its framework CI started without an approval click, and the release-date amend committed as the App bot (run 42081910035); #38's xargs fix ran on the real vault through the installed skill", date: 2026-11-05}
  - {rule_id: TST-VERIFY-03, followed: true, note: "gate commands come from CLAUDE.md and mirror framework.yml", date: 2026-11-03}
  - {rule_id: TST-VERIFY-04, followed: true, note: "the PR description lists what ran and what didn't", date: 2026-11-05}
  - {rule_id: DEV-CI-03, followed: true, note: "no infra dirs and no web surface, so iac-scan, a11y and lighthouse don't apply", date: 2026-11-04}
  - {rule_id: DEV-CI-04, followed: true, note: "the 'Protect main' ruleset requires the gate checks on every PR; no bypassed merge in #13-#32", date: 2026-11-04}
  - {rule_id: DEV-DEPS-01, followed: false, note: "toolchain pinned exactly in pyproject.toml, but transitive dependencies aren't locked (no lockfile yet)", date: 2026-11-04}
  - {rule_id: DEV-DEPS-03, followed: true, note: "majors read before merging (#13: vitest 4, zod 4); action majors (checkout v7, setup-python v7, gitleaks-action v3) deferred to Dependabot PRs", date: 2026-11-04}
  - {rule_id: DEV-DEPS-04, followed: true, note: "new CI dep actions/create-github-app-token: GitHub-maintained (actions org), MIT, active (pushed 2026-11-01); the documented way to mint App tokens in Actions; swiftui-template.yml adds github/codeql-action and actions/setup-go (both GitHub-maintained, MIT) and osv-scanner v2.7.0 (Google, Apache-2.0, active; release 2026-10-12), all pinned", date: 2026-11-05}
  - {rule_id: DEV-DEPS-05, followed: true, note: "create-github-app-token v3.3.0 and its SHA from GitHub releases; inputs (client-id over deprecated app-id) from its action.yml; GITHUB_TOKEN approval behaviour from GitHub docs", date: 2026-11-04}
  - {rule_id: DEV-DEPS-06, followed: false, note: "no monthly /evolve-standards fast-lane run yet", date: 2026-11-04}
  - {rule_id: DEV-GIT-05, followed: false, note: "every change since #4 went through a PR (the ruleset now requires it); the 2026-09-15 bootstrap commits went straight to main", date: 2026-11-04}
  - {rule_id: DEV-GIT-06, followed: true, note: "this period's PRs (#13-#32) each carry what changed, why, and a test plan with results", date: 2026-11-04}
  - {rule_id: DEV-REVIEW-01, followed: false, note: "nothing merged before 2026-11-05 got the T3 /code-review high rung: the bootstrap commits, #1-#40 (author PRs had self-review and most had Devin Review; Dependabot and release PRs only CI). Since then CLAUDE.md requires it before every push and on bot PRs. Flipping this also needs the DEV-REVIEW remediation: a retroactive review of everything merged before 2026-11-05, with follow-up fixes", date: 2026-11-05}
  - {rule_id: DEV-REVIEW-02, followed: false, note: "/security-review not yet run. No auth or crypto here, but run-verification.py runs each standard's verification cmd in the user's project, and the scanners and hooks run there too; since 2026-11-05 CLAUDE.md requires /security-review on changes to those. Flipping this also needs a retroactive /security-review of earlier changes to those surfaces (e.g. #12, #36, #38)", date: 2026-11-05}
  - {rule_id: DEV-REVIEW-03, followed: true, note: "every Devin finding and flag on #17-#32 was fixed or answered on the PR", date: 2026-11-04}
  - {rule_id: DEV-REVIEW-04, followed: true, note: "script bugfixes (#21, #25, #29, #31) began with failing tests", date: 2026-11-04}
  - {rule_id: LEG-LICENSING-02, followed: true, note: "no copyleft dependency: license metadata of all 37 toolchain packages checked", date: 2026-11-04}
  - {rule_id: LEG-LICENSING-03, followed: true, note: "BSL 1.1 LICENSE at the root", date: 2026-11-04}
  - {rule_id: LEG-LICENSING-04, followed: true, note: "no bundled fonts, icons or images", date: 2026-11-04}
  - {rule_id: SEC-CRYPTO-01, followed: true, note: "no cryptography in checks/, hooks/ or scripts/", date: 2026-11-04}
  - {rule_id: SEC-CRYPTO-03, followed: true, note: "no network traffic of its own; installs and API calls use HTTPS", date: 2026-11-04}
  - {rule_id: SEC-CRYPTO-04, followed: true, note: "no cryptographic choices made", date: 2026-11-04}
  - {rule_id: SEC-CRYPTO-05, followed: true, note: "no key material", date: 2026-11-04}
  - {rule_id: SEC-INPUT-01, followed: false, note: "inputs (GOVERNANCE.md, frontmatter) go through yaml.safe_load with hand-written validation in lint-framework and run-verification, not a schema library", date: 2026-11-04}
  - {rule_id: SEC-INPUT-04, followed: true, note: "no untrusted external input; paths come from the local user's CLI arguments", date: 2026-11-04}
  - {rule_id: SEC-INPUT-05, followed: true, note: "no file uploads", date: 2026-11-04}
  - {rule_id: SEC-INPUT-06, followed: true, note: "no URL fetching", date: 2026-11-04}
  - {rule_id: SEC-INPUT-07, followed: true, note: "no HTML rendering", date: 2026-11-04}
  - {rule_id: SEC-SAST-02, followed: true, note: "sast job in framework.yml runs checks/sec-sast.sh (bandit)", date: 2026-11-04}
  - {rule_id: SEC-SAST-03, followed: true, note: "every inline '# nosec' is B404/B603/B607 on an argv-only subprocess call and names its reason on the same line (grep); 1 '# noqa: B905' likewise", date: 2026-11-05}
  - {rule_id: SEC-SAST-04, followed: true, note: "semgrep considered and skipped: bandit covers the only stack here (Python); revisit if checks/ gains another language", date: 2026-11-04}
  - {rule_id: SEC-SECRETS-06, followed: true, note: "release App installed on this repo only, with Contents/Pull requests/Issues write; each run mints a 1-hour installation token that is revoked at job end; GITHUB_TOKEN narrowed to contents: write", date: 2026-11-04}
  - {rule_id: SEC-SUPPLY-02, followed: false, note: "no lockfile: the toolchain's top-level pins are exact but its transitive dependencies aren't locked", date: 2026-11-04}
  - {rule_id: SEC-SUPPLY-03, followed: true, note: "every action in .github/workflows is pinned to a commit SHA with a version comment, including create-github-app-token (grep: no tag refs)", date: 2026-11-04}
  - {rule_id: SEC-SUPPLY-04, followed: false, note: "exact top-level pins as for an application, but without the lockfile that STK-PY-06 pairs with them", date: 2026-11-04}
  - {rule_id: SEC-SUPPLY-05, followed: true, note: "no curl-pipe-to-shell; the toolchain comes from PyPI, each package one STK-PY names", date: 2026-11-04}
  - {rule_id: STK-PY-01, followed: true, note: "pyproject.toml is the single config home; checks/ is a script collection: no script imports another first-party module (checked); tests import the test helper checks/hostile_tree.py, which no script uses", date: 2026-11-05}
  - {rule_id: STK-PY-07, followed: true, note: "the toolchain is exactly STK-PY's (ruff, bandit, pip-audit, pytest, pytest-cov) plus PyYAML", date: 2026-11-04}
  - {rule_id: STK-PY-08, followed: true, note: "CLAUDE.md, scripts/ and CI call .venv/bin paths; the skills' system-python3 runs are by other projects, not this repo's commands", date: 2026-11-04}
  - {rule_id: TST-POLICY-04, followed: false, note: "coverage of checks/ is 75.96%; every checks/ script now has tests (build-index.py: test_build_index.py; import-cycles.py and silent-swallow.py: test_walkers.py and test_check_contract.py); depth at T3 weight (integration and end-to-end runs) not yet assessed", date: 2026-11-05}
  - {rule_id: TST-RATCHET-03, followed: true, note: "baseline first set at 39.56% in this change; never lowered", date: 2026-11-04}
  - {rule_id: TST-RATCHET-04, followed: true, note: "scripts/test.sh writes coverage.json (with subprocess-run scripts measured); coverage artifacts are gitignored", date: 2026-11-04}
```

## Notes

This manifest governs the ASPEC framework repo itself, not a project that uses it.

- **Tier T1** by the rubric: no payment or PII (line 1), no deployed service or running
  system others use (line 2), and the output is a framework rather than an analysis
  (line 3).
- **Published package** (`published_package: true`, ADR-0005): others install ASPEC, so
  the standards that opt in (SEC, TST, DEV, LEG licensing) are selected and verified at
  T3 weight. This replaces the earlier "known gap" note: `last_verified` now covers them.
- **Stack: python, as a script collection** (STK-PY-01): `checks/*.py` are standalone
  scripts run by path, none importing another first-party module, so there is no `src/`
  layout. `pyproject.toml` pins the toolchain (`[dependency-groups] dev`) and holds its
  config; tools run from `.venv/bin` (STK-PY-08).
- **Gates**: `scripts/lint.sh` (pre-commit) and `scripts/test.sh` (pre-push) are the same
  scripts CI's `lint` and `test` jobs run. CI adds `coverage-ratchet`, `sast` (bandit),
  `sca` (pip-audit), `gitleaks` and a no-op `typecheck` (DEV-CI-01's T3 job set).
  Coverage is measured including subprocess-run scripts; `.coverage-baseline` holds the floor.
- **Git hooks** are per clone: install with
  `GOVERNANCE_DIR=$PWD bash templates/scaffolds/_common/install-git-hooks.sh` (see
  CLAUDE.md).
- **Known shortfalls**, recorded as `followed: false` above (C9): no lockfile for the
  toolchain's transitive dependencies (DEV-DEPS-01, SEC-SUPPLY-02/04); `/code-review` and
  `/security-review` required only since 2026-11-05, with earlier merges not yet reviewed
  retroactively (DEV-REVIEW-01/02); test depth at T3 weight not yet assessed (TST-POLICY-04);
  input validation by hand rather than a schema library (SEC-INPUT-01).
- **Release secrets:** `release.yml` authenticates as a GitHub App installed on this repo
  only — client ID in the `RELEASE_APP_CLIENT_ID` repository variable, private key in
  the `RELEASE_APP_PRIVATE_KEY` Actions secret. Rotate the key in the App's settings and
  replace the secret; nothing is stored locally.
- **Approvals (C7):** pushing branches and opening PRs (2026-10-28). The maintainer
  approves and merges every PR, release-please's included. The 2026-11-04 approval to
  squash-merge clean PRs was withdrawn on 2026-11-05, after #38 was merged while a
  non-required CodeQL check was still pending.
