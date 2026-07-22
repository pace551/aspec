# CLAUDE.md — todomini (examples/htmx)

Worked example for STK-HTMX: a FastAPI + Jinja2 + htmx todo mini-app showing
HX-Request branching, progressive enhancement, CSRF double-submit, and hx-indicator.

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
todomini/
├── pyproject.toml                  # STK-PY single config home, src/ layout
├── src/app/main.py                 # routes; is_hx() branching; CSRF dependency
├── src/app/templates/base.html     # layout shell; loads vendored /static/htmx.min.js
├── src/app/templates/index.html    # full page; includes the list partial
├── src/app/templates/partials/todo_list.html  # the ONE list markup (both modes)
├── src/app/static/htmx.min.js      # vendored htmx (no runtime CDN dependency)
├── tests/test_app.py               # TestClient: full page + fragment + no-JS + CSRF
└── scripts/{lint.sh,test.sh}       # the scripts contract
```

## Commands

All commands runnable verbatim from repo root (no activation, no cd — STK-PY-08):

```bash
scripts/lint.sh        # ruff check + format check (same gate as pre-commit hook and CI)
scripts/test.sh        # pytest + coverage (same gate as pre-push hook and CI)
.venv/bin/uvicorn app.main:app --reload   # run the thing (http://localhost:8000)
```

First-time setup: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`

## Gotchas

- The store is in-memory: state resets on restart, and tests reset it per-test via
  `store.reset()`. Swap in SQLite behind `TodoStore` without touching routes.
- bandit is part of the STK-PY gate; no skips are configured for this project.
- The CSRF cookie is intentionally not `httponly` (the double-submit pattern needs no
  JS read here because forms carry the token server-rendered — keep it `samesite=lax`).
