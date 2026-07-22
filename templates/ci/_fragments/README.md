# CI Fragments

Canonical GitHub Actions **job snippets**, one file per gate. Per-stack workflows in
`templates/ci/{stack}.yml` are concrete compositions of these; `/bootstrap-repo` copies
the stack workflow and prunes jobs the project's tier doesn't require (per `DEV-CI`).

Conventions:

- Each fragment is a complete `jobs:`-level entry. Placeholders use `{{NAME}}` and are
  resolved by the stack workflow or `/bootstrap-repo`:
  - `{{CMD_LINT}}` `{{CMD_TYPECHECK}}` `{{CMD_TEST_COV}}` — the stack's commands, always
    the same ones the local `scripts/lint.sh` / `scripts/test.sh` run (one source of truth
    for what "passing" means; hooks and CI never disagree).
  - `{{SETUP_STEPS}}` — the stack's toolchain setup block (see stack workflows).
- Every job pins actions to a major version tag; at T3+ `SEC-SUPPLY` upgrades pins to
  full commit SHAs (`/bootstrap-repo --tier T3` does this mechanically).
- Required job set per tier is defined in `DEV-CI` (checks/dev-ci-present.sh verifies).

| Fragment | Gate | Tier |
|---|---|---|
| `lint.yml` | format + lint | T3+ CI (T1/T2 via pre-commit hook) |
| `typecheck.yml` | static types | T3+ (stacks with a typechecker) |
| `test.yml` | unit/integration tests | T3+ CI (T1/T2 via pre-push hook) |
| `coverage-ratchet.yml` | coverage never decreases | T2+ |
| `gitleaks.yml` | secret scan | all tiers with CI |
| `sast.yml` | static security analysis | T2+ |
| `sca.yml` | dependency vulnerabilities | T2+ |
| `iac-scan.yml` | tflint + checkov on infra | any tier with infra dirs |
| `a11y.yml` | axe-core on key pages | T3+ web |
| `lighthouse.yml` | Lighthouse CI perf budget | T3+ web |
| `license-audit.yml` | dependency license allowlist | T4 |
