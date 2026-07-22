# Scaffold: python (STK-PY)

Copied by `/bootstrap-repo` for new Python projects. On copy, bootstrap:

1. Renames `src/{{package}}/` to the real package name and fills `{{PROJECT_NAME}}` /
   `{{ONE_LINE_DESCRIPTION}}` in `pyproject.toml`.
2. Layers in `_common/` (CLAUDE.md.seed → `CLAUDE.md`, GOVERNANCE.md.seed →
   `GOVERNANCE.md`, appends `gitignore-base` to `.gitignore`, installs git hooks via
   `install-git-hooks.sh`).
3. Creates the venv: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`.

Scripts contract (`_common/README.md`): hooks, CI (`templates/ci/python.yml`), and
`/verify-compliance` all run `scripts/lint.sh` and `scripts/test.sh` — nothing defines
"passing" twice. All tool invocations are `.venv/bin/...` paths, never activation
(STK-PY-08).

Worked example built from this scaffold: `examples/python/`.
