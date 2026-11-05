---
id: STK-PY
title: Python Stack
family: STK
version: 1.0.5
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [python]
triggers:
  - python
  - pyproject
  - pytest
  - pip
  - venv
  - ruff
  - fastapi
  - pandas
requires: [SEC-SECRETS]
verification:
  - cmd: ".venv/bin/ruff check ."
    expect: "exit 0"
    layer: G
    rules: [STK-PY-03]
  - cmd: ".venv/bin/ruff format --check ."
    expect: "exit 0"
    layer: G
    rules: [STK-PY-03]
  - cmd: "sh -c 'if [ -d src ]; then .venv/bin/bandit -r src -q; elif [ -f pyproject.toml ]; then .venv/bin/bandit -c pyproject.toml -r . -q -x \".svn,CVS,.bzr,.hg,.git,__pycache__,.tox,.eggs,*.egg,/.venv/,/venv/,/node_modules/\"; else .venv/bin/bandit -r . -q -x \".svn,CVS,.bzr,.hg,.git,__pycache__,.tox,.eggs,*.egg,/.venv/,/venv/,/node_modules/\"; fi'"
    expect: "exit 0 (skips justified per STK-PY-04)"
    layer: G
    rules: [STK-PY-04]
  - cmd: ".venv/bin/pip-audit"
    expect: "exit 0 (per-CVE waivers handled by /verify-compliance)"
    layer: G
    rules: [STK-PY-05]
    tiers: [T2, T3, T4]
  - cmd: "sh -c '.venv/bin/pytest -q; rc=$?; [ $rc -eq 0 ] || [ $rc -eq 5 ]'"
    expect: "exit 0 — tests green (exit 5 'no tests collected' tolerated for fresh scaffolds; TST-POLICY governs test existence)"
    layer: G
    rules: [STK-PY-02]
  - cmd: "sh -c '.venv/bin/pytest -q --cov --cov-report=json >/dev/null 2>&1; \"$GOVERNANCE_DIR/.venv/bin/python\" \"$GOVERNANCE_DIR/checks/coverage-ratchet.py\" --check'"
    expect: "coverage ≥ committed .coverage-baseline (read-only check)"
    layer: G
    rules: [STK-PY-02]
    tiers: [T2, T3, T4]
  - cmd: "attest: pyproject.toml is the single config home, with src/ layout (or a script collection whose scripts import no first-party module)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PY-01]
  - cmd: "attest: dependency pinning matches project kind (apps exact via lockfile, libraries lower-bounded)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PY-06]
    tiers: [T2, T3, T4]
  - cmd: "attest: canonical-library table consulted for any new dependency"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PY-07]
  - cmd: "attest: all documented commands use .venv/bin paths, never activation"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PY-08]
last_review: 2026-11-05
---

# Python Stack (STK-PY)

## Abstract

House rules for every Python project, codifying the conventions proven in the `oracle/`
suite: one `pyproject.toml` as the single config home, `src/` layout for packages, a dedicated `.venv`
invoked by path (never activation), ruff for lint+format, bandit and pip-audit as security
gates, pytest with the coverage ratchet. Identical toolchain at every tier — what scales
with tier is test depth and CI, not which tools run. Scaffold:
`templates/scaffolds/python/` · CI: `templates/ci/python.yml` · worked example:
`examples/python/`.

## Normative Rules

### STK-PY-01 — `pyproject.toml` MUST be the single configuration home, with `src/` layout for packages

**Tiers**: all required — **Layer**: A (attestation; structure is set once at bootstrap)

Project metadata, dependencies, and tool config (`[tool.ruff]`, `[tool.pytest.ini_options]`,
`[tool.coverage.*]`) live in `pyproject.toml`. No `setup.py`, `setup.cfg`, `.flake8`,
`requirements.txt`-as-source-of-truth (a lockfile export is fine, see STK-PY-06). Code
lives under `src/{package}/`, tests under `tests/` — the src layout is what makes "it
imports because CWD is the repo" bugs impossible.

That bug needs first-party imports, so the layout rule is for **packages**: any project
whose code is imported, whether by its own modules, by other projects, or by being built
and installed. A **script collection** is exempt from it: standalone scripts run by path,
where no script imports another first-party module (tooling and ops repos). Its scripts
live in one named directory, its tests may sit beside them and load scripts by file path
(`importlib`), never through the working directory, and `pyproject.toml` still holds
everything else (`[tool.pytest.ini_options] testpaths`, `[tool.bandit] exclude_dirs` for
STK-PY-04). The line is bright: once two scripts share a helper module, it is a package
and moves to `src/`.

### STK-PY-02 — Tests MUST run via pytest and coverage MUST never drop below the committed baseline

**Tiers**: all required — **Layer**: G

`pytest` is the only runner; test policy (what gets tested first, integration scope) is
`TST-POLICY`'s job. "Pytest green" is required at every tier; the coverage ratchet runs at
T2+ (see the tier-scoped verification entries). The ratchet compares `--cov` output
against `.coverage-baseline` via `checks/coverage-ratchet.py`; the baseline only moves up. Python floor is 3.11; new
projects start on the current stable (3.14 today). `numba` note from oracle: keep it an
optional extra — no hard dependency on packages lacking current-CPython wheels.

### STK-PY-03 — ruff MUST pass with the house config for both lint and format

**Tiers**: all required — **Layer**: G

House config, verbatim from oracle (extend per-project, never weaken silently):

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "W"]
```

`ruff format` replaces black. Rule suppressions are inline `# noqa: XXX` with a reason,
never blanket `ignore` lists added to make CI green.

### STK-PY-04 — bandit MUST pass over `src/` (a script collection's repo), with every skip justified

**Tiers**: all required — **Layer**: G

`bandit -r src -q`; a script collection (STK-PY-01) scans the repo with its
`[tool.bandit] exclude_dirs`: `bandit -c pyproject.toml -r . -q -x <excludes>`, where
`<excludes>` is bandit's default list plus `/.venv/,/venv/,/node_modules/` (`-x` replaces
the defaults), so virtualenvs and `node_modules/` stay out of a repo-wide scan whatever
the config says. Skips are declared per-project (e.g. oracle's
`-s B101,B107,B110,B112`) and each skipped check gets a one-line justification in the
project `CLAUDE.md` or CI file. `# nosec` inline requires a trailing comment saying why.
SQL construction, `subprocess`, `pickle`, and `yaml.load` findings are never skipped —
fixed (parameterize, `shell=False`, safe formats, `yaml.safe_load`).

### STK-PY-05 — pip-audit MUST be clean, or findings waived per-CVE

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

Run against the environment (`.venv/bin/pip-audit`). A finding is either fixed by upgrade
or waived as `{rule_id: STK-PY-05, reason: "CVE-XXXX not reachable because …", expires}` in
`GOVERNANCE.md` — one waiver per CVE, never a standing "ignore vulnerabilities" state.
Cadence and auto-update policy live in `DEV-DEPS`.

### STK-PY-06 — Dependency versions: applications pin exact, libraries bound below

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Applications (anything deployed or scheduled) pin exact versions via a lockfile
(`uv lock`, `pip-compile`, or exported `requirements.txt` with `==`). Libraries declare
lower bounds (`>=`) plus known-bad exclusions. T2 research additionally records the exact
environment (`pip freeze > env-freeze.txt`) alongside results for reproducibility.

### STK-PY-07 — New dependencies SHOULD come from the canonical-libraries table

**Tiers**: all advisory — **Layer**: A (attestation)

| Need | Use | Not | Why |
|---|---|---|---|
| HTTP client | `httpx` | `requests`, raw `urllib` | async-capable, timeouts required at construction |
| Validation/models | `pydantic` v2 | hand-rolled dict checks | typed, fails loudly at the boundary |
| CLI | `argparse` (small) / `typer` (multi-command) | `click` directly, `sys.argv` parsing | one idiom per repo |
| Config files | `pyyaml` (`safe_load` only) + pydantic model | `configparser`, `json` for human-edited config | matches existing settings.yaml convention |
| Dataframes | `pandas` (default) / `polars` (perf-critical) | mixing both in one project | pick one per project |
| Dates | stdlib `datetime` + `zoneinfo`, aware everywhere | `pytz`, naive datetimes | naive datetimes are ARC-level bugs |
| Task scheduling | launchd/cron + plain script | in-process schedulers for T1 | matches existing plist convention |
| Testing | `pytest` + `pytest-cov` | `unittest` style classes | fixtures over inheritance |

Deviating is fine with a reason (that's SHOULD) — the point is that the choice is made
once, here, not re-litigated per session.

### STK-PY-08 — Tools MUST be invoked by venv path, never by activation state

**Tiers**: all required — **Layer**: A (attestation; enforced socially by scaffold + CLAUDE.md)

Every command in docs, CI, scripts, and skills is written `.venv/bin/pytest`,
`.venv/bin/ruff` — never "activate then run". Activation-dependent commands break in
launchd jobs, CI, and sub-agent shells (the exact failure class fixed in the
mortgage-scheduler launchd work). Each project's `CLAUDE.md` lists runnable commands in
this form.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `.venv/bin/ruff check .` | exit 0 | STK-PY-03 |
| 2 | `.venv/bin/ruff format --check .` | exit 0 | STK-PY-03 |
| 3 | `.venv/bin/bandit` over `src/`, or `-c pyproject.toml -r .` for a script collection | exit 0 | STK-PY-04 |
| 4 | `.venv/bin/pip-audit` (T2+) | exit 0 / per-CVE waivers | STK-PY-05 |
| 5 | `.venv/bin/pytest -q` | exit 0 (or 5: no tests yet) | STK-PY-02 |
| 6 | pytest `--cov` → `coverage-ratchet.py --check` (T2+) | ≥ `.coverage-baseline` | STK-PY-02 |
| 7-10 | attestation checklist (one per rule) | explicit yes | STK-PY-01, -06, -07, -08 |

**Remediation:** ruff import-order errors → `.venv/bin/ruff check --fix .` · bandit B608
(SQL) → parameterized queries, never f-strings into SQL · pip-audit hit → try upgrade
first; waive per-CVE only with unreachability argument · ratchet fail → add tests for the
new code, don't lower the baseline.

## Worked Example

`examples/python/` is the living example. Minimal shape:

```
myproj/
├── pyproject.toml        # metadata + deps + ruff/pytest/coverage config
├── .venv/                # python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
├── .coverage-baseline    # written by first ratchet run, committed
├── .env.example          # per SEC-SECRETS
├── CLAUDE.md             # commands in .venv/bin form, bandit skips justified
├── GOVERNANCE.md
├── src/myproj/__init__.py
└── tests/test_core.py
```

```toml
[project]
name = "myproj"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7", "pytest-cov>=4", "ruff>=0.4", "bandit>=1.7", "pip-audit>=2.6"]
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `source .venv/bin/activate` in scripts/CI | Breaks under launchd/CI/sub-agents | `.venv/bin/<tool>` paths (STK-PY-08) |
| Flat layout (`myproj.py` beside tests) | Imports work only from repo root; masks packaging bugs | `src/` layout (STK-PY-01) |
| A "script collection" whose scripts import a shared helper module | The CWD-import bug is back, under an exemption meant for standalone scripts | It's a package now: move to `src/` (STK-PY-01) |
| f-string / `%` SQL construction | Injection; bandit B608 | Parameterized queries (driver placeholders) |
| Blanket `[tool.ruff.lint] ignore = [...]` to silence CI | Erases the signal permanently | Fix, or inline `# noqa` with reason |
| `pip install` into system Python | Version drift across projects; sudo traps | Per-project `.venv` (STK-PY-02) |
| Hard dependency on numba/etc. without current wheels | Blocks interpreter upgrades (3.14 lesson) | Optional extra + pure-Python fallback |
| `yaml.load` on config | Arbitrary object construction | `yaml.safe_load` (STK-PY-04) |

## References

- oracle `backtest-rigor/pyproject.toml` + `CLAUDE.md` — the proven source of these
  conventions (ruff config transcribed verbatim).
- ruff docs (rule sets E,F,I,UP,B,W) — chosen set balances signal vs churn.
- Python Packaging User Guide, src layout discussion — rationale for STK-PY-01.
- pip-audit / OSV database — the SCA backend for STK-PY-05.

## Changelog

- **1.0.5** (2026-11-05) — STK-PY-04's repo-wide bandit scan (a script collection, or a project without `src/`) adds `-x` with bandit's default excludes plus `/.venv/,/venv/,/node_modules/`: without a `[tool.bandit] exclude_dirs` entry for them, bandit scanned the project's virtualenv and `node_modules/` and failed on third-party code. Matches `checks/sec-sast.sh`. No rule changes.
- **1.0.4** (2026-11-05) — Framework scripts run on the governance repo's `.venv` (`"$GOVERNANCE_DIR/.venv/bin/python"`, built by `checks/install.sh` with Python 3.11+) instead of the first `python3` on PATH, which can be an end-of-life Python. No rule changes.
- **1.0.3** (2026-11-04) — STK-PY-01's `src/` layout applies to packages; a script collection (standalone scripts run by path, none importing another first-party module) keeps its scripts in one directory with tests beside them. STK-PY-04's check scans `src/`, or otherwise the repo with `-c pyproject.toml` so a script collection's `[tool.bandit]` exclusions apply (`checks/sec-sast.sh` likewise). Adds no requirement: `src/` projects behave as before.
- **1.0.2** (2026-10-27) — Portability: framework check scripts referenced via `$GOVERNANCE_DIR` (exported by run-verification.py) instead of a hardcoded home-directory path.
- **1.0.1** (2026-07-22) — Format-review fixes: per-entry tier scoping, single-rule
  attestations, pytest exit-5 tolerance on fresh scaffolds, ratchet runs read-only.
- **1.0.0** (2026-07-22) — Initial version (pilot standard; transcribes oracle conventions).
