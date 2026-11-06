# Changelog — ASPEC

Framework-level changes (structure, tooling, skills, constitution). Individual standards
carry their own per-file changelogs.

## Unreleased

- **AI-EVALS** (ADR-0006): a new standard for projects that call an LLM, plus the `llm`
  stack key that selects it. `/govern` sets `llm` when the dependencies name an LLM SDK by
  exact package name, and AI-EVALS is then pinned at every tier with no trigger word
  needed. Eight rules:
  - an in-repo eval set built from real failures
  - outcome-first grading, with transcript checks on properties rather than exact tool
    sequences
  - at least 3 isolated trials at T2+
  - deterministic graders, and calibrated LLM judges
  - a regression gate
  - safety suites that must pass every trial
  - a clean held-out split
  - production feedback at T3+

  At T1 only the eval set and the safety suites are required. New
  `checks/eval-ratchet.py` backs them without calling a model. The project's runner
  writes a fresh `evals/results.json`, and `--stamp` hashes the tracked files listed in
  `evals/inputs` into it (it refuses results that are already stamped). `--check` fails
  on fewer than 10 cases and on a safety suite below 1.0 or relabelled. At T2+ it also
  fails on stale results or untracked input files, on fewer than 3 trials, and on a
  suite that is missing, ran fewer cases or times than its baseline, or dropped below the
  committed `.eval-baseline` by more than a noise band sized by the baseline's runs. At
  T1 those T2+ failures only warn. `--update-baseline` raises the bar deliberately, and
  lowering it needs `--allow-lower` plus a waiver. The gate refuses symlinked results and
  baseline files and writes atomically, so a hostile repo can't aim its writes elsewhere. AI-ARCH-02 now points to AI-EVALS (1.0.1, see-also only).

- `templates/ci/swiftui.yml`: hosted CI for the swiftui stack, for public repositories,
  where GitHub's standard macOS runners and CodeQL are free. A T3+ or published Swift
  project was asked for DEV-CI's job set with no template to build it from. Swift work
  (lint, typecheck, tests with coverage, CodeQL sast) runs once on `macos-latest`;
  gitleaks, the coverage ratchet, sca (osv-scanner v2.7.0) and license-audit run on
  Linux. typecheck also runs the new `scripts/lockfile-check.py`: whatever
  `swift package resolve` pins, transitive remote packages included, must match the
  `Package.resolved` committed to git, so a dependency can't skip sca and license-audit
  by going unpinned. The scaffold's `scripts/test.sh` now writes
  `lcov.info` (via the new `scripts/coverage.sh`) where full Xcode is installed, so the
  hooks' coverage ratchet works for Swift. New `scripts/sca.sh` scans every SwiftPM
  lockfile, Xcode's included. New `scripts/license-audit.py`: no tool reports SwiftPM
  licenses, so `licenses.allow` records each dependency's reviewed license per source
  URL and version (a fork or a new version is reviewed again).
  A path-filtered workflow
  (`.github/workflows/swiftui-template.yml`) runs those commands on `examples/swiftui`
  and checks that osv-scanner flags a known-vulnerable `Package.resolved`. STK-SWIFT-06
  still describes local verification as the default; private repos are unchanged.
  Its first macOS run also found that the scaffold's `scripts/lint.sh` never worked
  with swiftformat installed: current SwiftFormat rejects `swiftformat --lint Sources
  Tests` ("--lint argument does not expect a value"), so it now passes the paths first,
  and the example and scaffold sources are now formatted to SwiftFormat's defaults
  (with a `.swift-version` so its version-dependent rules apply). A `.swiftlint.yml`
  makes SwiftLint require the trailing commas SwiftFormat adds, instead of forbidding
  them: with both installed, `lint.sh` could never pass.

- `checks/build-index.py` refuses a standard whose `version` changed unless its
  `last_review` moved later or is today, and a `last_review` that isn't a date or is
  after today (with a day's slack for time zones). It also leaves the `last_review:`
  line out of the content hash: it used to refuse the `last_review`-only touch that the
  `/evolve-standards` staleness sweep makes, which that skill documents as exempt from a
  version bump. `checks/.index-hashes.json` now records `last_review`; hashes in the old
  format are still read.
- The scaffold pre-push hook (`templates/scaffolds/_common/githooks/pre-push`) runs
  `scripts/pre-push.sh` after the test and ratchet gates when a project has one, passing
  on the hook's arguments and the pushed refs (DEV-BOOTSTRAP 1.0.4, patch). Projects
  without the script see no change.
- This repo's PR rules are now a check. `checks/pr-hygiene.py` fails a branch that has
  more than one commit since its merge base, a subject that isn't a conventional commit
  (git's `Revert "…"` and `Reapply "…"` around one count), or a `feat`, `fix` or breaking
  change (`!` or a `BREAKING CHANGE:` footer) that adds no words to CHANGELOG.md's
  `## Unreleased` section (rewrapping, reordering, deleting or adding a subheading doesn't
  count). A revert of an unreleased change removes its entry (the entries holding lines
  `git blame` gives to the reverted commit, compared whole, so a rewrap isn't a removal);
  once a release has shipped the change, the revert adds an entry of its own. It runs in
  the new
  `pr-hygiene` job of `framework.yml` (pull requests, skipped when a bot opened the PR)
  and, per pushed branch, from this repo's `scripts/pre-push.sh`.
- Git exports `GIT_DIR` to hooks run from a linked worktree, and test suites that build
  throwaway git repos then act on the real one: run that way, this repo's own tests
  committed into the pushing repository. The scaffold pre-push hook now runs
  `scripts/test.sh` without the repository-location variables git reports in
  `git rev-parse --local-env-vars` (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`,
  `GIT_COMMON_DIR`, `git -c` settings and others), and this repo's
  `checks/conftest.py` drops `GIT_*` for its own test session.
- Every check ASPEC ships now has a contract test (`checks/test_check_contract.py`):
  each non-attestation verification cmd in `standards/` either has a known-bad project it
  must fail, or sits on an allowlist with a reason (it runs the project's own toolchain,
  needs the network, or is covered by another test). Checks that search the tree also
  run against hostile trees (`checks/hostile_tree.py`): the bad file under a path with
  spaces and non-ASCII, the bad file's directory unreadable (must fail, never pass
  silently), and unreadable gitignored `node_modules/` and `.venv/` plus a symlink loop
  (must still pass). It found:
  - 20 verification cmds in 12 standards that passed when a file couldn't be read: grep's
    error went to `/dev/null` or past `! … | grep -q .`, and `git grep` exits 1 ("no
    match") after "failed to stat". They now run the new `checks/grep-gate.py`
    (`forbid` / `require` a pattern in the files `git ls-files` selects; submodules,
    nested repos, symlinks and binaries skipped), which exits 2 for a file it can't
    read. INF-CONTAINERS 1.0.5, INF-EDGE 1.0.2, INF-ENVS 1.0.3,
    INF-SERVERLESS 1.0.4, STK-DDB 1.0.2, STK-NEXT 1.0.2, STK-PG 1.0.1, STK-REDIS 1.0.1,
    STK-SWIFT 1.0.2, STK-VITE 1.0.2 (patch bumps, no rule changes).
  - `git ls-files | grep …$` sees a path under a non-ASCII directory quoted, so a
    tracked `.tfstate` or `.log` there passed and a committed `.terraform.lock.hcl` there
    failed. INF-TF 1.0.3 and OPS-OBS 1.0.1 match by pathspec instead.
  - `checks/secret-scan.sh`'s fallback scan sent grep's errors to `/dev/null`, so a
    tracked file it couldn't read passed unscanned; it now exits 2 (scan incomplete),
    running grep under `LC_ALL=C` so the error text it checks is the same everywhere.
  - `checks/sec-sast.sh` ran bandit over `.venv/` and `node_modules/` in a repo-wide
    scan (failing on third-party code), and bandit skips an unreadable directory with
    exit 0. It now passes `-x` with bandit's default excludes plus
    `/.venv/,/venv/,/node_modules/` (`-x` replaces the defaults), and stops with exit 2
    when `find` can't list the tree. STK-PY 1.0.5 adds the same `-x` to STK-PY-04's cmd.
  - `checks/silent-swallow.py` skipped a tracked file it couldn't stat
    (`Path.is_file()` is False then), and `checks/import-cycles.py` walked with
    `Path.rglob`, which skips an unreadable directory. Both now take their files from
    `git ls-files` (import-cycles adds untracked, unignored files), so ignored caches and
    volumes are never entered, and exit 2 for anything else they can't read. Outside a
    git work tree they walk instead, with the same rule; a git failure inside one is an
    incomplete scan, not a reason to walk.
- `checks/lint-framework.py` checks references. Every `checks/…`, `templates/…` and
  `skills/…` path named in skills, docs, standards, the constitution, templates' prose,
  README and CLAUDE.md must exist: bare, after `$GOV/` or `$GOVERNANCE_DIR/` (quoted or
  not), or as a relative link. A glob must match something, and a bare `templates/<x>`
  counts only when `<x>` is a framework entry, since projects have Jinja and email
  templates of their own. Every `ADR-NNNN` outside standards and templates must have a
  file in `decisions/`, and a `pip install` in docs' code may only name packages
  `pyproject.toml` pins. Stale docs that still named a removed step or tool were a
  recurring Devin finding.
- New `checks/test_tier_matrix.py`. For every tier × published flag × stack with a CI
  template, wherever `select-standards.py` selects DEV-CI at T3/T4 weight, that stack's
  `templates/ci/<stack>.yml` must pass `dev-ci-present.sh` at that tier (#29: a published
  T1 package got DEV-CI at T3 weight but not the CI to match). It also checks that
  DEV-CI-01's job table, `dev-ci-present.sh` and `templates/ci/_fragments/` name the same
  jobs, that every scaffold stack has a CI template (or a stated reason: swiftui verifies
  locally by design, which leaves a T3+ or published Swift project with no template for
  DEV-CI), and that `/bootstrap-repo`'s T1 and T2 rules defer to its published-package
  rule, which they now say outright.

## 0.3.1 — 2026-11-05

- File lists reach `xargs` NUL-separated, so paths with spaces aren't split. `/evolve-standards`
  found no learning notes at all: every note `/harvest-learnings` writes is named
  `YYYY-MM-DD governance <slug>.md`, and its candidate search also piped to `rg`, which
  `xargs` can't run where `rg` is only a shell function (Claude Code). Step 1 is now
  `grep -rl --null … | xargs -0 grep -l …` with the vault path quoted. INF-ENVS 1.0.2,
  INF-CONTAINERS 1.0.4 and INF-SERVERLESS 1.0.3 had verification commands that passed a
  noncompliant workflow, Dockerfile or `.tf` file whose path held a space; ARC-MODULARITY
  1.0.3 fixes its file-size one-liner (all patch bumps). `lint-framework` rejects a piped
  `xargs` without `-0`/`--null` in standards and skills, reading xargs' options by arity
  (`-n 1 -0` is safe; `-P0` and `-I0` set a value of 0 and aren't). `checks/inf-container-scan.sh`
  and `checks/inf-tf-scan.sh` looped over a word-split list, so `svc a/Dockerfile` or
  `infra/my mod/` reached hadolint, trivy, tofu, tflint and checkov as two paths; they now
  read `find -print0` into bash arrays (bash 3.2-safe). A directory `find` can't enter
  now stops either scanner with exit 2 ("scan incomplete") instead of being skipped, and
  the excluded trees (`.git`, `node_modules`, `.venv`, `.terraform`) are pruned rather than
  walked, so an unreadable one can't abort the scan.
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
