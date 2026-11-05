# CLAUDE.md — ASPEC (Agent Safety, Performance, Enforcement & Compliance)

This repo IS the ASPEC governance framework other projects load. Changes here propagate to
every future task, so this repo holds itself to its own strictest rules.

## Working in this repo

- **Any edit to a file in `standards/` requires**: `version` bump (semver), a `## Changelog`
  entry, then `.venv/bin/python checks/build-index.py` (it refuses unbumped edits) and
  `.venv/bin/python checks/lint-framework.py` clean before commit.
- **Never hand-edit** `index.json`, `INDEX.md`, or `checks/.index-hashes.json` — generated.
- **Framework-shape changes** (frontmatter schema, tier model, new family, enforcement
  layers) need an ADR in `decisions/` first.
- **Rule IDs are permanent.** Never renumber; retire with strikethrough + note instead.
- The format contract is `templates/standard-template.md` — new standards start from it.
  The pilot standards (`standards/security/sec-secrets.md`, `standards/stacks/stk-py.md`)
  are the calibration references for depth and tone.
- **PRs are always a single squashed commit.** Fixups during review get squashed into
  the PR's one commit on the branch and force-pushed with `--force-with-lease`.
- **Framework changes get a `CHANGELOG.md` entry under `## Unreleased`** (hand-written
  prose). Releases are cut by merging release-please's release PR (`.github/workflows/
  release.yml`); it moves those entries under the version heading and sets the LICENSE
  Change Date via `checks/release-prep.py`. Never edit `version.txt` or
  `.release-please-manifest.json` by hand.
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
python3.14 -m venv .venv && .venv/bin/pip install --group dev   # once: pinned toolchain (pyproject.toml)
.venv/bin/python checks/build-index.py           # regenerate catalog
.venv/bin/python checks/build-index.py --check   # freshness check only
.venv/bin/python checks/lint-framework.py        # self-lint everything
scripts/lint.sh                         # lint gate (pre-commit hook, CI lint): self-lint, ruff, shell syntax
scripts/test.sh                         # test gate (pre-push hook, CI test): pytest + coverage.json
.venv/bin/python checks/coverage-ratchet.py --check   # coverage never below .coverage-baseline
checks/secret-scan.sh --staged          # pre-commit secret gate
GOVERNANCE_DIR=$PWD .venv/bin/python checks/run-verification.py --project .   # this repo's own /verify-compliance
```

Tools run from `.venv/bin` by path, never by activation (STK-PY-08). Once per clone,
install the git hooks (DEV-BOOTSTRAP-06):
`GOVERNANCE_DIR=$PWD bash templates/scaffolds/_common/install-git-hooks.sh`. It creates
the gitignored `.githooks/` and `.governance/`.

This repo's own tier, pins, and approvals live in `GOVERNANCE.md`: T1, published package
(ADR-0005), Python script collection (STK-PY-01).

The skills run `checks/` scripts with the system `python3` (3.9 on macOS), so they stay
3.9-compatible at runtime. `gitleaks` optional (scripts fall back to pattern scan);
install with `brew install gitleaks` for full coverage.
