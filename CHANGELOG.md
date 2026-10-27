# Changelog — ASPEC

Framework-level changes (structure, tooling, skills, constitution). Individual standards
carry their own per-file changelogs.

## Unreleased

- Portability: verification commands and scaffolds resolve the governance repo via
  `GOVERNANCE_DIR` (exported by run-verification.py) instead of a hardcoded home
  path; lint-framework rejects hardcoded home and absolute governance-repo paths
  in cmds and bodies (covered by `checks/test_lint_framework.py`); select-standards
  expands `~` in `--governance-dir`/`GOVERNANCE_DIR` and fails loudly on a non-repo;
  dev-bootstrap hook-install example corrected to match /bootstrap-repo.

## 0.1.0 — 2026-07-22

- Initial framework build: constitution (C1–C10), tier model (T1–T4), glossary,
  standard template + schema, index/lint tooling, secret-scan + coverage-ratchet checks,
  templates (GOVERNANCE/adr/waiver/obsidian), ADRs 0001–0003, pilot standards
  (SEC-SECRETS, STK-PY), then full 67-standard corpus, scaffolds, CI templates,
  examples, and the five governance skills.
