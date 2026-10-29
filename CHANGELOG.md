# Changelog — ASPEC

Framework-level changes (structure, tooling, skills, constitution). Individual standards
carry their own per-file changelogs.

## Unreleased

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
