---
id: STK-HTMX
title: Server-Rendered + htmx Stack
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [htmx, python, web]
triggers:
  - htmx
  - hypermedia
  - jinja
  - jinja2
  - fastapi
  - server-rendered
  - crud
  - form
  - partial
  - template
requires: [STK-PY]
verification:
  - cmd: "scripts/test.sh"
    expect: "exit 0 — pytest green via httpx TestClient, both full-page and partial responses asserted (exit 5 'no tests collected' tolerated on a fresh scaffold)"
    layer: G
    rules: [STK-HTMX-02, STK-HTMX-07]
  - cmd: "scripts/lint.sh"
    expect: "exit 0 — ruff check + format per STK-PY, run through the scripts contract"
    layer: G
    rules: [STK-HTMX-07]
  - cmd: "attest: stack is FastAPI + Jinja2 + htmx and the app is request/response shaped (mostly CRUD, minimal client state)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-HTMX-01]
  - cmd: "attest: state-changing actions work without JavaScript (plain form POST + redirect), or infeasible cases are noted in GOVERNANCE.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-HTMX-03]
  - cmd: "attest: every state-changing request carries CSRF protection (token in form + cookie comparison)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-HTMX-04]
  - cmd: "attest: every hx-triggered request has an hx-indicator and submit controls disable while in flight"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-HTMX-05]
  - cmd: "attest: no JSON endpoint exists for the app's own UI; any JSON route serves a documented machine consumer"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-HTMX-06]
last_review: 2026-07-22
---

# Server-Rendered + htmx Stack (STK-HTMX)

## Abstract

Rules for server-rendered web apps with htmx — the house default for mostly-CRUD,
form-driven tools with minimal client state, which is most T1/T3 internal work. The
pairing is FastAPI + Jinja2 + htmx on top of STK-PY. Handlers branch on the
`HX-Request` header — fragment for htmx, full page otherwise — from one set of
templates. Actions work without JavaScript where feasible, state-changing POSTs carry
CSRF protection, every in-flight request shows an `hx-indicator`, and there is no
parallel JSON API: the hypermedia is the API. Tests drive the app through httpx's
TestClient and assert both response modes. Scaffold: `templates/scaffolds/htmx/` ·
CI: `templates/ci/htmx.yml` · worked example: `examples/htmx/`.

## Normative Rules

### STK-HTMX-01 — The stack MUST be FastAPI + Jinja2 + htmx, chosen where the app is request/response shaped

**Tiers**: all required — **Layer**: A (attestation)

This stack fits when interactions are forms, lists, and detail views — server owns
all state, the client holds none worth naming. That is most internal tools. It is the
wrong choice for rich client interactivity (offline edits, optimistic drag-and-drop,
canvas — use STK-VITE) and unnecessary for React-ecosystem content sites (STK-NEXT).
One template engine (Jinja2), one interactivity layer (htmx); mixing in a second
front-end framework "for one widget" forfeits the stack's simplicity.

### STK-HTMX-02 — Handlers MUST branch on the `HX-Request` header: fragment for htmx, full page otherwise

**Tiers**: all required — **Layer**: G (scripts/test.sh; asserted by the project's own tests)

Every route serves both audiences: an htmx request (`HX-Request: true`) gets just the
partial it will swap in; a direct visit, refresh, or bookmark gets the full page. The
partial is the same Jinja include/block the full page composes — markup exists once.
This is what keeps URLs real: no route may exist that only works as a swap target.

### STK-HTMX-03 — State-changing actions SHOULD work without JavaScript

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Progressive enhancement: every mutating control is a real
`<form method="post" action="…">`; `hx-post`/`hx-target` enhance it. A non-htmx POST
responds `303 See Other` back to the page (POST/redirect/GET), so the app remains
usable with JS disabled or htmx failed-to-load. Where no-JS genuinely can't work
(e.g. drag-to-reorder), note the exception in `GOVERNANCE.md` — the default is
feasible far more often than assumed.

### STK-HTMX-04 — State-changing requests MUST carry CSRF protection

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Cookie-authenticated form posts are exactly what CSRF attacks; every non-GET route
validates a token. The house mechanism is double-submit: a `csrf_token` cookie
(`SameSite=Lax` minimum) compared against a hidden form field — htmx inherits it
because it submits the enclosing form's fields. `hx-headers` works for non-form
verbs (`hx-delete`). The scaffold ships this as middleware; removing it needs a
waiver, not a shrug.

### STK-HTMX-05 — In-flight requests MUST show an `hx-indicator`

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

UX-FORMS' loading state, hypermedia edition: each hx-triggering element (or its form)
declares `hx-indicator` pointing at a spinner/status element, and submit buttons
disable while the request runs (`hx-disabled-elt="this"`). Nothing feels more broken
than a click that silently does work.

### STK-HTMX-06 — A parallel JSON API MUST NOT be built for the app's own UI

**Tiers**: all required — **Layer**: A (attestation)

The hypermedia is the API: routes return HTML, and the UI consumes only that.
Duplicating each action as a JSON endpoint doubles the validation/authz surface and
recreates the client-state problem this stack exists to avoid. JSON routes are
allowed only for genuine machine consumers (cron jobs, another service, an export)
and are documented as such in the project `CLAUDE.md`.

### STK-HTMX-07 — Tests MUST drive the app through httpx's TestClient, asserting both response modes

**Tiers**: all required — **Layer**: G

`fastapi.testclient.TestClient` (httpx) hits real routes: full-page GETs assert the
layout shell is present; the same route with `HX-Request: true` asserts a bare
fragment (no `<html>`); non-htmx POSTs assert the 303 redirect. Gates run through the
scripts contract — `scripts/lint.sh` (ruff, per STK-PY) and `scripts/test.sh`
(pytest + coverage) — so hooks, CI, and `/verify-compliance` agree.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `scripts/test.sh` | exit 0 — pytest green (exit 5 tolerated on fresh scaffold) | STK-HTMX-02, -07 |
| 2 | `scripts/lint.sh` | exit 0 — ruff check + format (STK-PY house config) | STK-HTMX-07 |
| 3-7 | attestation checklist (one per rule) | explicit yes | STK-HTMX-01, -03, -04, -05, -06 |

**Remediation:** partial leaking a full `<html>` shell → render the include/block,
not the page template, on the `HX-Request` branch · CSRF 403 in tests → use the
scaffold's client helper that carries cookie + token · swap works but URL never
changes on navigation-like actions → add `hx-push-url="true"`.

## Worked Example

`examples/htmx/` is the living example — a todo mini-app:

```
examples/htmx/
├── pyproject.toml               # fastapi, jinja2, htmx-free server side (STK-PY layout)
├── src/app/main.py              # routes branch on HX-Request; CSRF middleware
├── src/app/templates/base.html  # layout shell; loads static/htmx.min.js
├── src/app/templates/index.html # full page: extends base, includes partials
├── src/app/templates/partials/todo_list.html   # the ONE list markup, used by both modes
├── tests/test_app.py            # TestClient: full page, partial, no-JS POST, CSRF
└── scripts/{lint.sh,test.sh}
```

```python
# src/app/main.py (core pattern)
def is_hx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"

@app.post("/todos")
async def create_todo(request: Request, title: str = Form(...)):
    todo = store.add(title)
    if is_hx(request):
        return templates.TemplateResponse(
            request, "partials/todo_list.html", {"todos": store.all()})
    return RedirectResponse("/", status_code=303)   # no-JS path (STK-HTMX-03)
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Separate `/api/…` JSON routes consumed by custom JS | Duplicated validation/authz; client state creeps back | HTML responses; hypermedia is the API (STK-HTMX-06) |
| Partial-only routes (404/naked fragment on direct visit) | Refresh and bookmarks break; URLs stop being real | Branch on `HX-Request` from one route (STK-HTMX-02) |
| Duplicated markup: one template for the page, another for the swap | The two drift; bugs appear in only one mode | Partials via Jinja includes composed by the page |
| `<div hx-post="…">` as the only way to mutate | No-JS users (and htmx load failures) dead-end | Real `<form>` enhanced by htmx (STK-HTMX-03) |
| Skipping CSRF "because htmx sends custom headers" | Plain form posts (the no-JS path) remain forgeable | Double-submit token middleware (STK-HTMX-04) |
| Returning 200 + error text into the swap target | Looks like success to htmx; error styling lost | 4xx with an error fragment, or `hx-retarget` the message region |
| Building a React island for one interactive widget | Two frontend stacks to govern, bundle + build complexity | htmx patterns (or reclassify the app to STK-VITE) |

## References

- htmx docs, `HX-Request` header + `hx-indicator` — the mechanisms behind
  STK-HTMX-02/-05.
- *Hypermedia Systems* (Gross/Gross/Carson) — the hypermedia-is-the-API argument
  behind STK-HTMX-06.
- OWASP CSRF Prevention Cheat Sheet (double-submit cookie pattern) — basis for
  STK-HTMX-04.
- FastAPI docs, templates + TestClient — the house testing mechanism (STK-HTMX-07).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
