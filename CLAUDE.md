# CLAUDE.md — ASPEC (Agent Safety, Performance, Enforcement & Compliance)

This repo IS the ASPEC governance framework other projects load. Changes here propagate to
every future task, so this repo holds itself to its own strictest rules.

## Working in this repo

- **Any edit to a file in `standards/` requires**: `version` bump (semver), `last_review`
  set to today, a `## Changelog` entry, then `.venv/bin/python checks/build-index.py` (it
  refuses an edit without a bump, and a bump whose `last_review` isn't later or today) and
  `.venv/bin/python checks/lint-framework.py` clean before commit. A `last_review`-only
  touch (the `/evolve-standards` staleness sweep) needs no bump.
- **Never hand-edit** `index.json`, `INDEX.md`, or `checks/.index-hashes.json` — generated.
- **Framework-shape changes** (frontmatter schema, tier model, new family, enforcement
  layers) need an ADR in `decisions/` first.
- **Rule IDs are permanent.** Never renumber; retire with strikethrough + note instead.
- The format contract is `templates/standard-template.md` — new standards start from it.
  The pilot standards (`standards/security/sec-secrets.md`, `standards/stacks/stk-py.md`)
  are the calibration references for depth and tone.
- **PRs are always a single squashed commit.** Fixups during review get squashed into
  the PR's one commit on the branch and force-pushed with `--force-with-lease`.
  `checks/pr-hygiene.py` enforces this and the CHANGELOG rule below (CI `pr-hygiene` job,
  and `scripts/pre-push.sh` from the pre-push hook).
- **Review before every push.** ASPEC is a published package, so DEV-REVIEW applies at
  T3 weight: `/code-review high` on every PR (DEV-REVIEW-01).
  - Before the first push of a PR branch, run `/code-review high` on the branch. After a
    fixup, review only what changed since the last push (`git range-diff` against the
    pushed branch if it was also rebased), not the whole branch again: re-running a full
    review until it comes back clean is an anti-pattern.
  - Fix or decline every finding with a reason (DEV-REVIEW-03), and list each finding and
    its outcome in the PR description so the record lives on the PR.
  - Run `/security-review` as well when the change touches input parsing or anything that
    runs on a user's machine or in their project (DEV-REVIEW-02): any `checks/` script
    (including `install.sh`), `hooks/`, `templates/` (scaffolds, git hooks, CI
    workflows), or a `verification` `cmd:` in `standards/`.
  - Push only after that. Devin Review comes after the push, as a second reviewer rather
    than the first.
  - PRs opened by bots (Dependabot, release-please) get `/code-review high <PR#>` before
    they are handed to the maintainer to merge. Record the outcomes in a PR comment: the
    bots rewrite their PR descriptions.
- **Framework changes get a `CHANGELOG.md` entry under `## Unreleased`** (hand-written
  prose); `feat`, `fix` and breaking changes must add one. Releases are cut by merging
  release-please's release PR (`.github/workflows/release.yml`); it moves those entries
  under the version heading and sets the LICENSE Change Date via `checks/release-prep.py`.
  Never edit `version.txt` or `.release-please-manifest.json` by hand.
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
scripts/pre-push.sh                     # PR hygiene (pre-push hook, CI pr-hygiene): one commit, CHANGELOG
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

Skills and standards run `checks/` scripts on `$GOVERNANCE_DIR/.venv/bin/python`, which
`checks/install.sh` builds with Python 3.11+; `lint-framework` rejects a bare `python3`
launch. The exception is `coverage-ratchet.py`, which is vendored into projects and run by
their own `python3`, so it stays 3.9-compatible (tested). `gitleaks` optional (scripts fall
back to pattern scan); install with `brew install gitleaks` for full coverage.
