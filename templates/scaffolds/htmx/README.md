# Scaffold: htmx (FastAPI + Jinja2 + htmx) — STK-HTMX

Copied into a new project by `/bootstrap-repo`, which also:

- fills `{{PROJECT_NAME}}` in `pyproject.toml`,
- merges `_common/` (gitignore-base, `.env.example`, `CLAUDE.md`, `GOVERNANCE.md`, git hooks),
- creates the venv: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`,
- downloads htmx into `static/htmx.min.js`
  (`curl -fsSL https://unpkg.com/htmx.org@2/dist/htmx.min.js -o src/app/static/htmx.min.js`)
  so the app has no runtime CDN dependency (T3+ supply-chain posture; a CDN tag is
  acceptable at T1 if you prefer).

Scripts contract (hooks, CI, and /verify-compliance all run these):

- `scripts/lint.sh` — ruff check + ruff format --check (STK-PY house config)
- `scripts/test.sh` — pytest + coverage (exit 5 "no tests" tolerated on fresh scaffold)

The package is `src/app/` (import name `app`) regardless of project name — routes in
`app.main`, templates under `src/app/templates/`, partials in
`src/app/templates/partials/` (the same fragments the full pages include: STK-HTMX-02).
