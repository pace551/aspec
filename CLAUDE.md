# CLAUDE.md — ASPEC (Agent Safety, Performance, Enforcement & Compliance)

This repo IS the ASPEC governance framework other projects load. Changes here propagate to
every future task, so this repo holds itself to its own strictest rules.

## Working in this repo

- **Any edit to a file in `standards/` requires**: `version` bump (semver), a `## Changelog`
  entry, then `python3 checks/build-index.py` (it refuses unbumped edits) and
  `python3 checks/lint-framework.py` clean before commit.
- **Never hand-edit** `index.json`, `INDEX.md`, or `checks/.index-hashes.json` — generated.
- **Framework-shape changes** (frontmatter schema, tier model, new family, enforcement
  layers) need an ADR in `decisions/` first.
- **Rule IDs are permanent.** Never renumber; retire with strikethrough + note instead.
- The format contract is `templates/standard-template.md` — new standards start from it.
  The pilot standards (`standards/security/sec-secrets.md`, `standards/stacks/stk-py.md`)
  are the calibration references for depth and tone.
- Skills in `skills/` are canonical; `checks/install.sh` copies them to `~/.claude/skills/`.
  Edit here, then reinstall — never edit the installed copies.

## Layout

```
constitution/   CONSTITUTION.md (always-loaded invariants), tiers.md, glossary.md
standards/      67 standards, 11 family dirs — frontmatter is the API
decisions/      framework ADRs
templates/      standard/GOVERNANCE/adr/waiver/obsidian templates, ci/, scaffolds/
skills/         govern, bootstrap-repo, verify-compliance, harvest-learnings, evolve-standards
checks/         build-index.py, lint-framework.py, secret-scan.sh, coverage-ratchet.py,
                per-standard verification scripts, install.sh
hooks/          Claude Code hook scripts (wired via ~/.claude/settings.json by install.sh)
examples/       per-stack worked examples + noncompliant-fixture (negative test)
```

## Commands

```bash
python3 checks/build-index.py           # regenerate catalog
python3 checks/build-index.py --check   # freshness check only
python3 checks/lint-framework.py        # self-lint everything
checks/secret-scan.sh --staged          # pre-commit secret gate
```

Python 3.14, PyYAML available system-wide. `gitleaks` optional (scripts fall back to
pattern scan); install with `brew install gitleaks` for full coverage.
