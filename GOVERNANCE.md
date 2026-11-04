# Governance Manifest

```yaml
tier: T1
classified: 2026-11-03
tier_override: null
stacks: []
standards:
  - {id: AI-SECURITY, version: 1.0.1}
  - {id: DEV-BOOTSTRAP, version: 1.0.2}
  - {id: DEV-GIT, version: 1.0.2}
  - {id: OPS-FINOPS, version: 1.0.0}
  - {id: SEC-SECRETS, version: 1.0.2}
  - {id: TST-FIXTURES, version: 1.0.1}
  - {id: TST-POLICY, version: 1.0.0}
  - {id: TST-VERIFY, version: 1.0.0}
waivers: []
external_action_approvals:
  - {action: "push branches and open pull requests on github.com/pace551/aspec", granted: 2026-10-28}
pii_inventory: n/a
last_verified: 2026-11-03
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
  - {rule_id: SEC-SECRETS-03, followed: true, note: "no secrets used; CI uses only the built-in GITHUB_TOKEN", date: 2026-11-03}
  - {rule_id: SEC-SECRETS-04, followed: true, note: "none observed this session; secret-scan and full-history gitleaks clean", date: 2026-11-03}
  - {rule_id: SEC-SECRETS-05, followed: true, note: "no secret known to have been exposed", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-01, followed: true, note: "test data is synthetic; the noncompliant-fixture's secrets are deliberate fakes (.gitleaksignore)", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-02, followed: true, note: "no randomness or wall-clock use in checks/test_*.py (grep); dates are passed explicitly; each test builds its own temp dir", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-03, followed: true, note: "no network libraries in tests (grep); git tests use local file:// remotes", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-04, followed: false, note: "only the tests added this session (release-prep, git-gate) were checked: they build per-test data; older tests not audited", date: 2026-11-03}
  - {rule_id: TST-FIXTURES-05, followed: true, note: "no flaky test observed", date: 2026-11-03}
  - {rule_id: TST-POLICY-01, followed: true, note: "this changeset has no bugfix; this session's script bugfixes (#21 guard, #25 checks) began with failing tests; workflow-YAML fixes (#22) can't be unit-tested locally", date: 2026-11-03}
  - {rule_id: TST-POLICY-02, followed: true, note: "release-prep.py (#21) was written test-first", date: 2026-11-03}
  - {rule_id: TST-POLICY-03, followed: true, note: "scripts/*.sh are glue over existing gates; run directly, plus negative runs (Python 3.9 only, ruff violation)", date: 2026-11-03}
  - {rule_id: TST-POLICY-05, followed: true, note: "no coverage percentage gate anywhere in this repo's CI (grep)", date: 2026-11-03}
  - {rule_id: TST-VERIFY-01, followed: true, note: "lint (scripts/lint.sh), unit tests (scripts/test.sh), hooks on the real commit and push, then run-verification", date: 2026-11-03}
  - {rule_id: TST-VERIFY-02, followed: true, note: "scripts run directly and through the installed git hooks on this PR's own commit and push", date: 2026-11-03}
  - {rule_id: TST-VERIFY-03, followed: true, note: "gate commands come from CLAUDE.md and mirror framework.yml", date: 2026-11-03}
  - {rule_id: TST-VERIFY-04, followed: true, note: "the PR description lists what ran and what didn't", date: 2026-11-03}
```

## Notes

This manifest governs the ASPEC framework repo itself, not a project that uses it.

- **Tier T1** by the rubric: no payment or PII (line 1), no deployed service or running
  system others use (line 2), and the output is a framework rather than an analysis
  (line 3).
- **Known gap: the published-package carve-out is not verified.** This repo is a
  published package, so tiers.md says its supply-chain families (SEC, TST, DEV, LEG
  licensing) carry T3 weight. The tooling can't express that yet: pinning those standards
  under `tier: T1` would make run-verification skip their T3-scoped checks, and `tier: T3`
  would wrongly pull in service-only standards. So the pins above are the plain T1 set,
  and `last_verified` covers only them. Partial coverage outside verification: framework
  CI (self-lint, full-history gitleaks, pinned ruff), SHA-pinned actions in the write-token
  release workflow, least-privilege `GITHUB_TOKEN` permissions, and Dependabot. Closing
  the gap needs carve-out support in select-standards and run-verification (an ADR first,
  since it changes the tier model).
- **No stacks:** the root has no stack manifest. `checks/` scripts are covered by
  `scripts/lint.sh` (pre-commit) and `scripts/test.sh` (pre-push), which run the same steps
  as the framework CI's self-lint job. `examples/` carry their own GOVERNANCE.md files.
- **Git hooks** are per clone: install with
  `GOVERNANCE_DIR=$PWD bash templates/scaffolds/_common/install-git-hooks.sh` (see
  CLAUDE.md). There's no `.coverage-baseline`, so pre-push skips the ratchet; coverage
  isn't tracked for `checks/`.
- **Approvals (C7):** pushing branches and opening PRs was approved by the maintainer on
  2026-10-28. Merging stays with the maintainer; releases happen when the maintainer merges
  the release-please PR.
