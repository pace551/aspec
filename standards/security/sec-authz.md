---
id: SEC-AUTHZ
title: Authorization
family: SEC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - authorization
  - permissions
  - access control
  - idor
  - roles
  - admin
  - ownership
  - multi-tenant
  - iam
requires: []
verification:
  - cmd: "attest: access is denied by default — every route/resource requires an explicit grant, and unauthenticated reachability is the exception, not the accident"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHZ-01]
    tiers: [T3, T4]
  - cmd: "attest: every authorization decision is made server-side from server-held state; no role, id, or flag supplied by the client is trusted"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHZ-02]
    tiers: [T3, T4]
  - cmd: "attest: every object access verifies the caller's right to that specific object (IDOR check), not just that the caller is logged in"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHZ-03]
    tiers: [T3, T4]
  - cmd: "attest: service and CI roles carry least-privilege permissions scoped to what the code actually does"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHZ-04]
    tiers: [T3, T4]
  - cmd: "attest: admin functionality is separated from user surfaces and gated by its own authorization layer"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHZ-05]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Authorization (SEC-AUTHZ)

## Abstract

Authentication says who you are; authorization decides what you may do — and it is where
real-world APIs actually break (BOLA/IDOR has topped the OWASP API Top 10 since 2019).
Five invariants: deny by default, decide only server-side from server-held state, check
rights on every *specific object* touched, run services and CI on least-privilege roles,
and keep admin surfaces structurally separate. Advisory below T3 because a single-user
tool has no second principal to confuse — but the moment a second user or a public URL
exists, these are required and verified by attestation against the actual route table.

## Normative Rules

### SEC-AUTHZ-01 — Access MUST be denied by default

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every route, resource, and action starts closed; reachability is granted explicitly
(auth middleware applied globally with a short, named allowlist of public routes — not
bolted onto routes someone remembered). The failure this retires: the endpoint added in
a hurry that never got the decorator. New routes are secure the day they are born
because insecurity, not security, is what requires opting in. The same posture applies
to infra: security groups, bucket policies, and CORS (SEC-WEB-02) default closed.

### SEC-AUTHZ-02 — Authorization decisions MUST be made server-side from server-held state only

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The client is an untrusted renderer. Roles come from the server's session/user record —
never from a client-supplied header, cookie value, hidden form field, request body flag
(`"is_admin": true`), or an unverified JWT claim. Hiding a button is UX, not access
control: the request the button would have sent must be rejected server-side. JWT
claims count as server-held only after signature verification against the server's key,
and role-bearing tokens must be short-lived or revocable so a role change actually
takes effect.

### SEC-AUTHZ-03 — Every object access MUST verify the caller's right to that specific object

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

IDOR is the canonical failure: `GET /statements/17` checks that *someone* is logged in,
then serves statement 17 to anyone who increments the id. Every lookup by identifier
carries an ownership/permission predicate — `WHERE id = ? AND owner_id = ?`, or a
`get_owned_*` accessor that 404s on both missing and unowned (404, not 403: don't
confirm existence of what the caller can't see). Centralize the check in one accessor
per resource so it cannot be forgotten route-by-route. Applies equally to mutations,
list endpoints, and "export" jobs.

### SEC-AUTHZ-04 — Service and CI roles MUST carry least-privilege permissions

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The app's runtime role can read its own bucket and its own SSM path — not `s3:*` on
`*`. CI deploy roles are scoped to the resources they deploy, assumed via GitHub OIDC
rather than static keys (SEC-SECRETS-06, `INF-ENVS`). One role per service, so a
compromised component is bounded by its own blast radius instead of inheriting the
account. Start from empty and add permissions when something fails with AccessDenied —
that error message is the permission spec writing itself.

### SEC-AUTHZ-05 — Admin surfaces MUST be separated and independently gated

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Admin functionality lives under its own prefix (`/admin`) behind its own middleware
gate — checked server-side per SEC-AUTHZ-02 — and is never woven into user endpoints as
`?admin=true` branches. Obscurity (an unlinked URL) is not a gate. Prefer stronger
separation as stakes rise: at T4, an admin surface that isn't internet-routable at all
(VPN/tailnet, or a separate internal app) beats one protected only by a login form, and
admin logins get MFA per SEC-AUTHN-04.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: deny-by-default route/resource posture (T3+) | explicit yes recorded | SEC-AUTHZ-01 |
| 2 | attest: server-side decisions, no client-supplied authz data (T3+) | explicit yes recorded | SEC-AUTHZ-02 |
| 3 | attest: object-level (IDOR) checks on every access (T3+) | explicit yes recorded | SEC-AUTHZ-03 |
| 4 | attest: least-privilege service/CI roles (T3+) | explicit yes recorded | SEC-AUTHZ-04 |
| 5 | attest: admin surfaces separated and gated (T3+) | explicit yes recorded | SEC-AUTHZ-05 |

**Remediation:** route found without auth → apply middleware globally, allowlist the
truly-public routes by name · id-only lookups → add the ownership predicate to the shared
accessor and grep for raw `db.get(Model, id)` call sites · wildcard IAM → diff actual
AccessDenied-driven needs into a scoped policy · admin branch in a user route → extract
under `/admin` with its own gate. Before attesting, walk the route table once per rule —
the attestation is a claim about every endpoint, not a mood.

## Worked Example

Object-level authorization as a single reusable FastAPI dependency (SEC-AUTHZ-03), on
top of global deny-by-default middleware (SEC-AUTHZ-01):

```python
def get_owned_statement(
    statement_id: int,
    user: User = Depends(current_user),          # global auth dependency: deny by default
    db: Session = Depends(get_db),
) -> Statement:
    stmt = db.get(Statement, statement_id)
    if stmt is None or stmt.owner_id != user.id:  # missing and unowned are the same 404
        raise HTTPException(status_code=404)
    return stmt

@app.get("/statements/{statement_id}")
def read_statement(stmt: Statement = Depends(get_owned_statement)) -> StatementOut:
    return StatementOut.model_validate(stmt)
```

Every statement route depends on `get_owned_statement`; there is exactly one place the
check can be wrong, and zero places it can be forgotten. The matching least-privilege
runtime policy (SEC-AUTHZ-04): `s3:GetObject` on `arn:aws:s3:::myapp-statements/*` and
`ssm:GetParameter` on `/myapp/prod/*` — nothing else.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Auth decorator applied route-by-route | The forgotten route ships open; default-allow in practice | Global middleware + named public allowlist (SEC-AUTHZ-01) |
| Hiding the admin button in the UI | The API behind it still answers anyone | Server-side gate; UI hiding is UX only (SEC-AUTHZ-02) |
| Trusting `role` from an unverified JWT or request body | Client mints its own privileges | Server-held session state; verify signatures (SEC-AUTHZ-02) |
| `db.get(Model, id)` after login check | Textbook IDOR — enumerate ids, read everyone's data | Ownership predicate in one shared accessor (SEC-AUTHZ-03) |
| 403 for unowned, 404 for missing | Existence oracle for other users' objects | Uniform 404 (SEC-AUTHZ-03) |
| `AdministratorAccess` on the app's runtime role | One SSRF/RCE away from owning the AWS account | Least-privilege per service (SEC-AUTHZ-04) |
| Unlinked `/secret-admin` URL as the only gate | URLs leak: logs, referrers, browser history | Own middleware gate; ideally not internet-routable (SEC-AUTHZ-05) |

## References

- OWASP API Security Top 10 — API1 Broken Object Level Authorization; the reason
  SEC-AUTHZ-03 is the centerpiece rule.
- OWASP Authorization Cheat Sheet — deny-by-default and centralized-enforcement
  guidance behind SEC-AUTHZ-01/-03.
- OWASP Top 10 A01:2021 Broken Access Control — the category's #1 ranking justifies
  this standard's weight at T3+.
- AWS IAM policy grammar and "grant least privilege" docs — the mechanics for
  SEC-AUTHZ-04's scoped policies.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
