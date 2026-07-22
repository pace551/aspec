---
id: ARC-API
title: API Design
family: ARC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - api
  - rest
  - endpoint
  - http
  - route
  - openapi
  - swagger
  - pagination
  - versioning
  - fastapi
  - json api
  - status code
requires: []
verification:
  - cmd: "attest: endpoints are plural-noun resources with honest methods and status codes"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-01]
  - cmd: "attest: public routes carry a /v1-style path version; breaking changes bumped it"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-02]
  - cmd: "attest: every error response is RFC 9457 problem+json, safe for the caller's eyes"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-03]
  - cmd: "attest: collection endpoints use the items/next_cursor envelope with cursor pagination"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-04]
  - cmd: "attest: side-effecting POST endpoints accept an Idempotency-Key and replay the original result"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-05]
  - cmd: "attest: the OpenAPI spec is generated from code and documents auth, timeouts, and limits"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-06]
    tiers: [T3, T4]
  - cmd: "attest: any non-REST (RPC-ish) interface is internal-only with no consumer other than James"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-API-07]
last_review: 2026-07-22
---

# API Design (ARC-API)

## Abstract

REST-by-default conventions for any HTTP interface: plural-noun resources, `/v1` path
versioning, RFC 9457 `problem+json` errors, cursor pagination in a consistent envelope,
`Idempotency-Key` on side-effecting endpoints, and an OpenAPI spec generated from code.
Required once an API has consumers other than James (T3+), where every inconsistency
becomes someone else's workaround. At T1/T2 the ceremony is advisory and internal tools
MAY stay RPC-ish — the standard's job there is to keep accidental APIs from fossilizing
into unfixable ones.

## Normative Rules

### ARC-API-01 — Resources MUST be plural nouns with honest methods and status codes

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`GET /invoices`, `GET /invoices/{id}`, `POST /invoices`, `PATCH /invoices/{id}`,
`DELETE /invoices/{id}`. The method carries the verb; the path never does (`/getInvoices`
is the smell). Status codes tell the truth: `201` + `Location` on create, `204` on delete,
`404` vs `403` chosen deliberately, never `200` wrapping an error body. Actions with no
resource model MAY be an action sub-resource (`POST /invoices/{id}/send`) — sanctioned,
but rare.

### ARC-API-02 — Public APIs MUST version via a `/v1` path prefix from the first external release

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Path versioning (`/v1/invoices`) — not headers, not query params — because it is visible
in logs, curl-able, and cacheable. Additive changes (new fields, new endpoints) do not
bump the version; breaking changes (removed/renamed fields, changed semantics) do. At most
two versions live at once, with the old one's retirement date announced when `/v2` ships.

### ARC-API-03 — Error responses MUST be RFC 9457 `application/problem+json`

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every non-2xx body is a problem document: `type`, `title`, `status`, `detail`,
`instance`, plus an extension member carrying the correlation id (`OPS-OBS`). `detail` is
written for the caller — what happened, what to change — never a stack trace, ORM message,
or internal path (`ARC-ERRORS-06`; form-level presentation is `UX-FORMS`). One error shape
for the whole API, including validation errors (an `errors` extension array of
field/message pairs).

### ARC-API-04 — Collections MUST paginate with cursors inside a consistent envelope

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Collection responses are `{"items": [...], "next_cursor": "..."}` — never a bare array
(bare arrays can't grow metadata without breaking callers). Cursors are opaque strings;
`next_cursor: null` means done. Cursor over offset because offset pagination skips or
duplicates rows under concurrent writes and forces deep scans. Paginate from day one on
anything unbounded — retrofitting pagination is a breaking change (ARC-API-02).

### ARC-API-05 — Side-effecting endpoints MUST accept an `Idempotency-Key`

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every `POST` that creates a resource or triggers an external effect accepts an
`Idempotency-Key` header; a replayed key returns the originally-recorded response instead
of re-executing. Storage and semantics per `ARC-IDEMPOTENCY-03`. `PUT` and `DELETE` are
naturally idempotent — keep them that way (no counters or side effects hidden inside).

### ARC-API-06 — T3+ APIs MUST publish an OpenAPI spec generated from code

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Generated, never hand-written — hand-maintained specs drift the week they're born. With
FastAPI the served `/openapi.json` (typed route signatures + pydantic models) is the
artifact for free; other frameworks use their equivalent generator. The spec (or its
linked docs) states auth mechanism, server-side timeout, rate limits, and pagination
conventions, so a consumer never learns limits by tripping over them.

### ARC-API-07 — Internal T1/T2 tools MAY be RPC-ish

**Tiers**: all advisory — **Layer**: A (attestation)

A localhost dashboard or personal-automation endpoint may use function-shaped routes
(`POST /rebuild-index`) and plain JSON errors — REST ceremony buys nothing before there
are external consumers. Two disciplines survive even here: no `200`-wrapping-an-error
(ARC-API-01's honesty clause) and explicit timeouts (`ARC-ERRORS-02`). The moment a
second consumer or public URL appears, `/govern` re-tiers and the full standard applies.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–5 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-API-01…05 |
| 6 | attestation, T3+ only | explicit yes recorded | ARC-API-06 |
| 7 | attestation checklist | explicit yes recorded | ARC-API-07 |

**Remediation:** verbs in paths → rename routes, keep old paths as 308 redirects until the
next version bump · bare-array collections → wrap in the envelope during the next breaking
version (ARC-API-02) · mixed error shapes → add one exception handler that emits
problem+json for everything · hand-written spec drifting → delete it, generate from code.

## Worked Example

FastAPI fragment satisfying rules 01, 03, 04, 06:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="invoices", version="1.0.0")  # /openapi.json generated (ARC-API-06)

@app.exception_handler(Exception)
async def problem(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(                              # RFC 9457 (ARC-API-03)
        status_code=500, media_type="application/problem+json",
        content={"type": "about:blank", "title": "Internal error", "status": 500,
                 "detail": "Unexpected failure — retry with the same Idempotency-Key.",
                 "instance": request.url.path})

@app.get("/v1/invoices")                              # /v1 path (ARC-API-02)
async def list_invoices(cursor: str | None = None, limit: int = 50) -> dict:
    items, next_cursor = fetch_page(cursor, min(limit, 200))
    return {"items": items, "next_cursor": next_cursor}   # envelope (ARC-API-04)
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `200 OK` with `{"error": ...}` body | Breaks every client's happy-path assumption; invisible to monitoring | Honest status + problem+json (ARC-API-01/03) |
| Offset pagination (`?page=7`) on a growing table | Rows skipped/duplicated under writes; deep offsets scan | Opaque cursors (ARC-API-04) |
| Bare JSON array as a collection response | No place for `next_cursor`/metadata without breaking callers | `items` envelope from day one |
| Hand-maintained `swagger.yaml` | Drifts immediately; consumers trust a lie | Generate from code (ARC-API-06) |
| Stack trace in a 500 body | Leaks internals; useless to the caller | problem+json with correlation id (ARC-API-03) |
| Versioning via `Accept` header at this scale | Invisible in logs/curl; ceremony without benefit | `/v1` path prefix (ARC-API-02) |
| Retrofitting REST onto a T1 localhost tool | Ceremony with zero consumers | RPC-ish is sanctioned there (ARC-API-07) |

## References

- RFC 9457 (Problem Details for HTTP APIs) — the error format ARC-API-03 mandates;
  obsoletes RFC 7807.
- Stripe API reference — the industry exemplar of cursor pagination and idempotency keys
  that rules 04/05 copy.
- Zalando RESTful API Guidelines — the plural-noun/status-code conventions distilled into
  ARC-API-01.
- FastAPI OpenAPI docs — how the generated spec in ARC-API-06 falls out of typed routes.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
