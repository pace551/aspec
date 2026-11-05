# Changelog — ASPEC

Framework-level changes (structure, tooling, skills, constitution). Individual standards
carry their own per-file changelogs.

## Unreleased

- Release PRs no longer wait for a maintainer to approve their CI runs. GitHub holds the
  `pull_request` runs of any PR that `GITHUB_TOKEN` opens or pushes to, so
  `.github/workflows/release.yml` now mints a short-lived GitHub App installation token
  (`actions/create-github-app-token`) for release-please and for the release-date amend
  push. The App's client ID is the `RELEASE_APP_CLIENT_ID` repository variable and its
  private key the `RELEASE_APP_PRIVATE_KEY` secret. `GITHUB_TOKEN` keeps only
  `contents: write`, for editing the release notes.

## 0.3.0 — 2026-11-05

- Framework scripts run on a supported Python. `checks/install.sh` now builds the
  governance clone's `.venv` with Python 3.11+ and the pinned `runtime` dependency group
  (PyYAML), and syncs an existing one to those pins on every run; the skills (`/govern`, `/verify-compliance`,
  `/bootstrap-repo`, `/evolve-standards`) and the verification commands of 7 standards
  (TST-RATCHET, ARC-MODULARITY, ARC-ERRORS, STK-PY/TS/GO/RUST; patch bumps) launch
  `checks/*.py` through `"$GOVERNANCE_DIR/.venv/bin/python"` instead of the first
  `python3` on PATH, which on macOS is an end-of-life 3.9 that no test covered.
  `lint-framework` rejects a bare `python3` launch of a framework script in standards and
  skills. `coverage-ratchet.py`, vendored into projects and run by their own `python3`,
  stays 3.9-compatible and is tested on 3.9 where available. **Existing installs:** pull
  the governance clone and re-run `checks/install.sh` once to create the venv.
- The framework's own Python is a declared STK-PY script collection: `pyproject.toml`
  pins its toolchain (`[dependency-groups] dev`) and holds the house ruff config
  (STK-PY-03). `checks/` is formatted with `ruff format`, and the lint gate (hook and
  CI) checks formatting too. Markdown is excluded, so standards' code samples are
  untouched.
- Python script collections (STK-PY 1.0.3, SEC-SAST 1.0.3): STK-PY-01's `src/` layout now
  applies to packages. A script collection (standalone scripts run by path, none
  importing another first-party module) keeps its scripts in one directory with tests
  beside them; once scripts share a helper module it is a package and moves to `src/`.
  STK-PY-04's check and `sec-sast.sh` scan `src/`, or for a script collection the repo
  with `[tool.bandit]` exclusions. `src/` projects are unaffected. Covered by
  `checks/test_python_bandit_target.py`.
- tiers.md and ADR-0005 now state that `published_package` only adds requirements: a
  published package at T3/T4 (e.g. sold) keeps all tier-required standards, and waives
  any service-only one that doesn't apply rather than dropping it. Packages are
  classified by the full rubric (lines 3–4 are the usual outcome, not a rule), and
  `/govern` sets the flag for code others install even when the project also operates
  a service.
- Published packages (ADR-0005): the tiers.md carve-out now has tooling. A manifest sets
  `published_package: true`; every SEC, TST, DEV and LEG standard declares `published:
  required | advisory | n/a` (linted, optional elsewhere). For a published package,
  `select-standards.py --published` selects the opted-in standards at that
  applicability (never weaker than the tier's), and `run-verification.py` runs their
  checks at max(tier, T3). The 22 standards are classified per ADR-0005 (patch bumps:
  no project could carry the flag before). Each selected entry reports `effective_tier`,
  and `/govern` reads rule tier tags at it, so a published T1 package's brief keeps
  T3-required rules. `/govern` asks whether a project is published; `/bootstrap-repo`
  builds T3 CI, the coverage baseline and dependency-update automation for published
  packages at any tier. Templates (incl. the GOVERNANCE seed), AUTHORING.md, tiers.md
  and the guide document the flag. Covered by `checks/test_published_package.py`.
- `/bootstrap-repo` at T3+ now adds `renovate.json` (DEV-DEPS-02); a fresh T3 scaffold
  used to fail that check.
- The framework repo now governs itself, as a T1 published package (ADR-0005) whose
  Python is a STK-PY script collection. Its root `GOVERNANCE.md` pins 18 standards (the
  T1 set, the opted-in supply-chain standards at T3 weight, and STK-PY), records the
  maintainer's approvals (push/PR; merging PRs whose Devin review is clean and required
  checks pass), and holds 66 attestations, 13 marked not followed with their reasons;
  `/verify-compliance` passes all 29 checks. To get there: tools run from a `.venv`
  built from `pyproject.toml`'s pinned dev group; `scripts/lint.sh` and
  `scripts/test.sh` are the hook gates and the CI `lint`/`test` jobs; framework CI is
  DEV-CI's T3 job set (`lint`, `typecheck` no-op, `test`, `coverage-ratchet`, `sast`
  bandit, `sca` pip-audit, `gitleaks`) with actions pinned to commit SHAs; Dependabot
  sends grouped weekly updates for actions and the pip toolchain; coverage, including
  scripts run as subprocesses, has a committed baseline of 39.56%; argv-only subprocess
  calls carry reasoned `# nosec`. Git hooks install per clone (see CLAUDE.md);
  `.githooks/` and `.governance/` are gitignored here.
- Verification fixes for git gates (DEV-BOOTSTRAP 1.0.2, DEV-CI 1.0.2, DEV-GIT 1.0.2).
  The hook checks (DEV-BOOTSTRAP-06, DEV-CI-02) looked only in `.git/hooks/`, so every
  repo whose hooks came from `install-git-hooks.sh` (`core.hooksPath` = `.githooks`)
  failed them; they now ask `git rev-parse --git-path hooks`. The linear-history check
  (DEV-GIT-03) ran `git log --merges -20`, which returns merge commits from all of
  history, so a single old merge failed it forever; it now inspects the last 20 commits.
  Covered by `checks/test_git_gate_checks.py`.

## 0.2.0 — 2026-10-29

- Releases: release-please (`.github/workflows/release.yml`) keeps a release PR open
  from the conventional commits on `main`; merging it tags `vX.Y.Z` and publishes a
  GitHub release whose notes are this file's section for that version. The changelog
  stays hand-written (`skip-changelog`). On the release PR, `checks/release-prep.py`
  sets the LICENSE Change Date to the release date + 3 years and moves the Unreleased
  entries under the version heading; it refuses to fold entries into a version that
  already has a section. Covered by `checks/test_release_prep.py`. The workflow runs on
  every push to `main` and can be started by hand (Actions → release → Run workflow).
- License: the BSL Additional Use Grant now states that it does not cover offering
  ASPEC, or a derivative, to third parties as a product or service (sold, licensed,
  hosted, or bundled into a commercial offering). Using ASPEC to build commercial
  products is unchanged. Change Date moves to 2029-10-28 (publication + 3 years, the
  original offset); it is meant to move forward with each release. Versions already
  published keep the terms they were published under.
- License: the grant now says that software built with ASPEC, including code
  generated from or copied out of its templates and scaffolds, is not an offering of
  ASPEC under the resale exclusion, and may be distributed under terms of its
  author's choosing. Without this, a product built from a scaffold could be read as
  a "derivative" excluded from the grant.
- Coverage ratchet: "no coverage data" exits 3 instead of 2. Python exits 2 when it
  can't open a script, so TST-RATCHET's check (which tolerates "no data yet") used to
  pass when the ratchet script was missing. Covered by `checks/test_coverage_ratchet.py`.
- run-verification: a check that exceeds `--timeout` is now a FAIL row ("timed out
  after Ns") and the run continues. Previously the timeout raised an uncaught
  exception, so no report was printed, and processes the check had started in the
  background kept running. Each check now runs in its own process group, which is
  killed when the check finishes, times out, or the run is interrupted (Ctrl-C).
  Output is captured to temp files rather than pipes, so a child that detaches into
  its own session can't stall the report by holding the output open.
- Trigger matching: select-standards matches triggers on whole words with
  inflectional endings (-s/-es/-ed/-ing) instead of substrings; triggers of three
  characters or fewer match only exactly or with -s. Short triggers no longer fire
  inside other words ("decided" → `ci`, "stage" → `tag`, "share" → `sha`, "product"
  → `prod`, "going" → `go`), which used to pin unrelated advisory standards;
  inflected forms still match (`deploy` → "deployed", `retry` → "retries", `cache` →
  "caching"). Known limitation: brand names that are also verbs inflect
  (`stripe` → "striping").
- Version pins are enforced by semver level (ADR-0004): patch drift WARNs and runs the
  current checks; minor/major drift, a pin newer than the governance repo, or a
  non-semver pin FAILs that standard without running its checks. Previously any
  mismatch was only a WARN, so new rules reached projects silently under old pins.
- Stack keys: select-standards rejects unknown `--stacks` keys (usage error listing
  the allowed keys) instead of silently dropping the stack-scoped standards — e.g.
  `postgres` used to omit the always-required STK-PG. The canonical list moves to
  `checks/stack-keys.json` (shared by lint and the selector); /govern's
  stack-detection step now names the exact `postgresql`/`dynamodb` keys.
- Framework CI pins ruff (0.17.1) so lint rules can't change between runs; an
  unpinned install picked up new default rules mid-PR twice.
- Portability: verification commands and scaffolds resolve the governance repo via
  `GOVERNANCE_DIR` (exported by run-verification.py) instead of a hardcoded home
  path; lint-framework rejects hardcoded home and absolute governance-repo paths
  in cmds and bodies (covered by `checks/test_lint_framework.py`); select-standards
  expands `~` in `--governance-dir`/`GOVERNANCE_DIR` and fails loudly on a non-repo;
  dev-bootstrap hook-install example corrected to match /bootstrap-repo.
- install.sh works on a machine without `~/.claude`: it creates the directory
  before writing `aspec.json`, and `--hooks` creates `settings.json` when none exists
  (backing up only an existing one). Covered by `checks/test_install.py`.

## 0.1.0 — 2026-07-22

- Initial framework build: constitution (C1–C10), tier model (T1–T4), glossary,
  standard template + schema, index/lint tooling, secret-scan + coverage-ratchet checks,
  templates (GOVERNANCE/adr/waiver/obsidian), ADRs 0001–0003, pilot standards
  (SEC-SECRETS, STK-PY), then full 67-standard corpus, scaffolds, CI templates,
  examples, and the five governance skills.
