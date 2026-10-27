# Changelog — ASPEC

Framework-level changes (structure, tooling, skills, constitution). Individual standards
carry their own per-file changelogs.

## Unreleased

- Trigger matching: select-standards matches triggers on whole words with
  inflectional endings (-s/-es/-ed/-ing) instead of substrings; triggers of three
  characters or fewer match only exactly or with -s. Short triggers no longer fire
  inside other words ("decided" → `ci`, "stage" → `tag`, "share" → `sha`, "product"
  → `prod`, "going" → `go`), which used to pin unrelated advisory standards;
  inflected forms still match (`deploy` → "deployed", `retry` → "retries", `cache` →
  "caching"). Known limitation: brand names that are also verbs inflect
  (`stripe` → "striping").
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
