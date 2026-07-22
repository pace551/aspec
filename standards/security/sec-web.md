---
id: SEC-WEB
title: Web Hardening
family: SEC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [web]
triggers:
  - security headers
  - csp
  - hsts
  - cors
  - rate limit
  - cookies
  - clickjacking
  - web app
  - frontend
  - browser
requires: [SEC-INPUT]
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-web-headers.sh"
    expect: "exit 0 — required headers present on http://localhost:3000 (pass the real URL in CI; skips gracefully if the app is not running)"
    layer: G
    rules: [SEC-WEB-01]
  - cmd: "attest: cors is deny-by-default with an explicit origin allowlist; no wildcard origin, and never wildcard with credentials"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-WEB-02]
    tiers: [T3, T4]
  - cmd: "attest: auth and expensive endpoints are rate limited"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-WEB-03]
    tiers: [T3, T4]
  - cmd: "attest: every cookie carries the strictest flags it can bear (httpOnly, secure, samesite)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-WEB-04]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Web Hardening (SEC-WEB)

## Abstract

The browser enforces exactly the policy the server declares — declare nothing and you get
nothing. This standard is the declaration layer for anything browser-facing: security
headers (CSP, HSTS, `X-Content-Type-Options`, frame-ancestors) asserted by
`checks/sec-web-headers.sh` against the running app; CORS deny-by-default with named
origins; rate limits on auth and expensive endpoints at T3+; and maximal cookie flags.
It assumes SEC-INPUT (required co-load): escaping stops XSS payloads, these headers
contain whatever slips through. Advisory below T3 — a localhost dashboard has no hostile
origin — required the moment real users or a public URL exist.

## Normative Rules

### SEC-WEB-01 — Responses MUST carry the required security headers

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

| Header | Baseline value | What it retires |
|---|---|---|
| `Content-Security-Policy` | `default-src 'self'; frame-ancestors 'none'` — tighten/loosen per app, never absent | XSS payload execution, clickjacking |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (https only) | protocol-downgrade, cookie theft over http |
| `X-Content-Type-Options` | `nosniff` | MIME-sniffing uploads into scripts |
| frame protection | CSP `frame-ancestors` (preferred) or `X-Frame-Options: DENY` | clickjacking |
| `Referrer-Policy` (advisory) | `strict-origin-when-cross-origin` | URL/token leakage via referrer |

Set once in middleware or platform config, not per-route. A CSP with
`'unsafe-inline'` scripts is a starting point to be tightened (nonces/hashes), not an
end state. `checks/sec-web-headers.sh [URL]` asserts the required set on the running
app (default `http://localhost:3000`; skips with a warning when unreachable — CI starts
the app first, then checks).

### SEC-WEB-02 — CORS MUST be deny-by-default with an explicit origin allowlist

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

No CORS headers at all is the correct default — same-origin policy is the protection,
and most apps that serve their own frontend never need to relax it. When a
cross-origin consumer is real, name it: exact origins in the allowlist, no
`Access-Control-Allow-Origin: *` on anything authenticated, and never `*` (or blind
request-origin echoing, its moral equivalent) combined with
`Access-Control-Allow-Credentials: true`. Scope the relaxation to the routes that need
it, not the whole app. Remember CORS protects users from cross-site requests — it does
nothing against direct API calls, which is what SEC-AUTHN/SEC-AUTHZ are for.

### SEC-WEB-03 — Auth and expensive endpoints MUST be rate limited at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Two endpoint classes, two reasons: auth endpoints (login/signup/reset — the
SEC-AUTHN-05 set) because attackers script them, and expensive endpoints (search,
export, report generation, LLM-backed routes, anything fanning out to paid APIs)
because one loop can take the service down or run up a bill (C6 exposure). Enforce
per-IP and, where identity exists, per-account — at the edge (CloudFront/WAF, nginx
`limit_req`) or in app middleware (slowapi for FastAPI, express-rate-limit). Return
`429` with `Retry-After`; log limit hits so tuning is data-driven (`OPS-OBS`).

### SEC-WEB-04 — Cookies MUST carry the strictest flags they can bear

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Default template: `HttpOnly; Secure; SameSite=Lax; Path=/` — then justify each
loosening. `HttpOnly` off only for cookies JavaScript genuinely must read (rare);
`SameSite=None` only for a real embedded cross-site use case, and then always with
`Secure`. Session cookies get `SameSite=Lax` minimum (`Strict` where UX allows) and a
`__Host-` name prefix on https, which locks the cookie to the exact host with no
Domain override. Why the session cookie is the right token home at all is
SEC-AUTHN-03's argument; this rule is the flag reference for every cookie, session or
not.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/sec-web-headers.sh [URL]` | exit 0 — required headers present (skip with warning if app not running) | SEC-WEB-01 |
| 2 | attest: CORS deny-by-default, explicit origins (T3+) | explicit yes recorded | SEC-WEB-02 |
| 3 | attest: auth + expensive endpoints rate limited (T3+) | explicit yes recorded | SEC-WEB-03 |
| 4 | attest: strictest-bearable cookie flags (T3+) | explicit yes recorded | SEC-WEB-04 |

**Remediation:** missing headers → add the middleware from the Worked Example (one
place, all routes) · header check "passes" because the app wasn't running → start the
app; a skip is not a pass, CI must run it against a live port · `*` CORS on an
authenticated API → replace with the named frontend origin today · no rate limiting →
start with edge/middleware defaults (e.g. 5/min on login, 60/min general) and tune from
429 logs.

## Worked Example

FastAPI middleware setting the SEC-WEB-01 baseline in one place:

```python
from fastapi import FastAPI

app = FastAPI()

@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-ancestors 'none'"
    )
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp
```

Verified against the running app:

```
$ bash ~/Dev/claude-code/governance/checks/sec-web-headers.sh http://localhost:8000
sec-web-headers: note — HSTS check skipped for non-https URL
sec-web-headers: warning — advisory header absent: Permissions-Policy
sec-web-headers: pass (http://localhost:8000)
```

CORS for the one real cross-origin consumer, scoped and named (SEC-WEB-02):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],   # exact origin, no wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| No CSP because "we have no XSS" | The header exists for the XSS you don't know about | Baseline CSP now, tighten later (SEC-WEB-01) |
| CSP with `unsafe-inline` + `unsafe-eval` forever | Neutralizes script-src almost entirely | Nonces/hashes; treat unsafe-* as scaffolding |
| Headers set per-route in handlers | The forgotten route ships bare — same failure mode as per-route auth | One middleware, all responses (SEC-WEB-01) |
| `Access-Control-Allow-Origin: *` on an authenticated API | Any site can read responses via the user's browser | Named origin allowlist (SEC-WEB-02) |
| Echoing the request's Origin header back | Wildcard with extra steps — defeats the allowlist | Compare against a literal list |
| Rate limiting only login, not `/export` or LLM routes | The bill and the outage come from the expensive ones | Cover both classes (SEC-WEB-03) |
| `SameSite=None` without `Secure` | Rejected by modern browsers; plaintext-exposed elsewhere | `None` implies `Secure`, always (SEC-WEB-04) |
| Relying on CORS as authorization | CORS never stops curl | AuthZ is server-side (SEC-AUTHZ-02) |

## References

- MDN HTTP security header documentation (CSP, HSTS, X-Content-Type-Options,
  Referrer-Policy) — canonical semantics for the SEC-WEB-01 table.
- OWASP Secure Headers Project — the recommended-value baseline the table adapts to
  personal scale.
- MDN CORS documentation — the credentialed-request rules behind SEC-WEB-02's
  never-wildcard-with-credentials line.
- OWASP Cheat Sheets: Clickjacking Defense & Session Management — frame-ancestors
  preference and the `__Host-` prefix guidance in SEC-WEB-04.
- securityheaders.com — quick external scoring of a deployed app; useful manual
  complement to `sec-web-headers.sh`.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
