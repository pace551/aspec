---
name: bootstrap-repo
description: Use this skill when creating a new project repository, when /implement-spec reaches its Scaffold step, when the user types /bootstrap-repo, or when an existing repo needs governance retrofitted (missing GOVERNANCE.md, hooks, or CI). Copies the stack scaffold, composes tier-appropriate CI from fragments, installs git hooks, seeds CLAUDE.md/GOVERNANCE.md/.env.example, and verifies the fresh scaffold passes its own gates before handover.
---

# bootstrap-repo — governed project scaffolding

Stand up (or retrofit) a repo that passes `/verify-compliance` from its first commit.
Governance repo: `$GOV`.

## Steps

### 1. Intake

Need: project name/path, primary stack(s), tier, and whether it is a published package
(ADR-0005; fills `{{PUBLISHED_PACKAGE}}` with `true`/`false`). Any of these unknown → run `/govern`
first (it classifies and writes the manifest; this skill consumes it). Existing non-empty
directory → this is a RETROFIT: never overwrite existing files, only add missing ones,
and list what was added.

### 2. Scaffold

- Copy `$GOV/templates/scaffolds/{stack}/` for the primary stack (secondary data stacks:
  merge the fragment dir from `$GOV/templates/scaffolds/data/{store}/`).
- Apply `_common`: append `gitignore-base` to `.gitignore`, seed `.env.example`,
  `CLAUDE.md` and `GOVERNANCE.md` from the `.seed` files with `{{SLOTS}}` filled.
- `git init -b main` if not already a repo.
- Run `bash $GOV/templates/scaffolds/_common/install-git-hooks.sh` from the project root
  (installs `.githooks/` pre-commit + pre-push, vendors `.governance/` scripts).

### 3. CI (tier-dependent, per DEV-CI)

- **T1**: no CI files — the git hooks are the gates. Skip, unless it's a published
  package (below).
- **T2**: hooks + optionally the test workflow only; ask nothing, default to hooks-only.
  A published package builds CI anyway (below).
- **T3/T4**: copy `$GOV/templates/ci/{stack}.yml` → `.github/workflows/ci.yml`; prune
  jobs DEV-CI doesn't require for the tier; keep `{{…}}`-free (stack templates are
  concrete — if a placeholder survives, resolve it from the scaffold's scripts).
  T4: also add `license-audit`. T3+: pin action refs to SHAs per SEC-SUPPLY.
- **Published package** (`published_package: true`, ADR-0005), any tier: DEV-CI and
  SEC-SUPPLY are opted in, so build CI as for T3 (T4 if the tier is T4) even at T1/T2:
  the T3 job set, action refs pinned to SHAs.
- **T3+ and published packages**: add dependency-update automation (DEV-DEPS-02): the
  `renovate.json` from DEV-DEPS's Worked Example at the repo root. Enabling the Renovate
  GitHub app is manual; list it under step 6.

### 4. Baselines & stack init

Install the toolchain (create `.venv` + dev deps / `npm install` / `go mod tidy` /
`cargo build` as the stack requires). Then initialize the ratchet at T2+, or at any tier
for a published package (TST-RATCHET and DEV-BOOTSTRAP are opted in, ADR-0005):
run `scripts/test.sh` and `python3 .governance/coverage-ratchet.py` (writes
`.coverage-baseline`; commit it).

### 5. Self-verification gate (mandatory before handover)

The fresh scaffold MUST pass its own gates:

```bash
scripts/lint.sh && scripts/test.sh
$GOV/.venv/bin/python $GOV/checks/run-verification.py --project .
```

Then prove the hook bites: stage a file containing a fake canary secret
(`aws_key = "AKIAIOSFODNN7EXAMPLE1"` in a scratch file), attempt `git commit` — it must
be REJECTED by pre-commit; then remove the canary. If any of this fails, fix the
scaffold — never hand over a repo whose gates don't fire.

### 6. STOP — human review

Present: tree of what was created, gates verified (with the canary-rejection evidence),
CI jobs configured, and what remains manual (e.g. GitHub repo creation, branch
protection at T3+). Wait for the user before first push or any external action
(Constitution C7).

## Rules

- Never write real secrets anywhere; `.env.example` placeholders only (SEC-SECRETS).
- Retrofit mode adds, never replaces; report every file touched.
- Scaffold bugs you find are framework bugs: note them for `/harvest-learnings`.
