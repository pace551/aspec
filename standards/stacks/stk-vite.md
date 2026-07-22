---
id: STK-VITE
title: Vite + React SPA Stack
family: STK
version: 1.0.1
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [vite-react]
triggers:
  - vite
  - spa
  - react
  - dashboard
  - internal tool
  - tanstack
  - react query
  - react-router
  - single-page
requires: [STK-TS]
verification:
  - cmd: "scripts/lint.sh"
    expect: "exit 0 — prettier --check + eslint + tsc --noEmit (strict), same gate as pre-commit hook and CI"
    layer: G
    rules: [STK-VITE-08]
  - cmd: "scripts/test.sh"
    expect: "exit 0 — vitest + Testing Library green with coverage emitted (--passWithNoTests tolerates a fresh scaffold)"
    layer: G
    rules: [STK-VITE-08]
  - cmd: "sh -c '! git grep --untracked -InE \"VITE_[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PRIVATE|API_KEY|ACCESS_KEY|CREDENTIAL)\" 2>/dev/null'"
    expect: "exit 0 — no secret-shaped name behind the VITE_ prefix anywhere in the tree"
    layer: G
    rules: [STK-VITE-07]
  - cmd: "attest: this app is an internal tool/dashboard for known users; SPA choice recorded in GOVERNANCE.md notes"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-VITE-01]
  - cmd: "attest: all server state flows through TanStack Query; no fetch-in-useEffect anywhere"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-VITE-02]
  - cmd: "attest: routing uses react-router with route modules as the unit of structure"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-VITE-03]
  - cmd: "attest: every non-trivial form uses react-hook-form with a zod resolver"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-VITE-04]
  - cmd: "attest: every route has an error boundary and async UI renders loading/error/data states"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-VITE-05]
  - cmd: "attest: routes are code-split (React.lazy or route-level dynamic import)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-VITE-06]
last_review: 2026-07-22
---

# Vite + React SPA Stack (STK-VITE)

## Abstract

Rules for Vite + React single-page apps — the house choice for internal tools and
dashboards with known users only; public content sites use STK-NEXT or STK-HTMX
instead. Server state lives in TanStack Query (never fetch-in-useEffect, the canonical
anti-pattern), routing in react-router with route-level code-splitting and error
boundaries, forms in react-hook-form + zod, and nothing secret behind `VITE_`. Tests
are vitest + Testing Library and assert behavior, not implementation. Scaffold:
`templates/scaffolds/vite-react/` · CI: `templates/ci/vite-react.yml` · worked
example: `examples/vite-react/`.

## Normative Rules

### STK-VITE-01 — A SPA MUST be the justified choice, not the default

**Tiers**: all required — **Layer**: A (attestation)

SPAs fit internal tools and dashboards: known users, authenticated sessions, rich
client interactivity, SEO irrelevant. Public content sites MUST NOT ship as SPAs —
they get STK-NEXT (React ecosystem, SEO/SSR) or STK-HTMX (form-driven CRUD). Record
the choice and its reason in `GOVERNANCE.md` notes at bootstrap; "we know React" is
not a reason, "offline-capable data grid for one team" is.

### STK-VITE-02 — Server state MUST live in TanStack Query

**Tiers**: all required — **Layer**: A (attestation)

Every read is a `useQuery` with a structured query key; every write is a
`useMutation` that invalidates the keys it stales. Fetch-in-`useEffect` +
`setState` is the canonical anti-pattern: it has no cache, no deduplication, no
retry, races on unmount, and re-implements loading/error state per component.
`useState`/`useReducer` are for UI state only (open panels, selections) — anything
the server owns is server state.

### STK-VITE-03 — Routing MUST use react-router, with route modules as the unit of structure

**Tiers**: all required — **Layer**: A (attestation)

`createBrowserRouter` with a route object tree; each route module owns its component,
error boundary, and (where used) loader. State that identifies *where the user is* —
selected record, filters, tab — lives in the URL (params/search params), not in
component state, so links, refresh, and back/forward behave.

### STK-VITE-04 — Forms MUST use react-hook-form with zod resolvers

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

One zod schema per form drives both the resolver and the submit payload's type —
validation logic is never duplicated between UI checks and API calls. Errors render
per-field, and the submit handler is a mutation (STK-VITE-02), so the three-state
rule (STK-VITE-05) covers submission feedback. Client-side validation is UX, not
security — the server revalidates (SEC-INPUT).

### STK-VITE-05 — Every route MUST have an error boundary; async UI MUST render its three states

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

react-router's `errorElement` (or an `ErrorBoundary` component) at each route keeps a
render error contained to the pane it broke, with a retry path — never a white
screen. Every query-driven view handles all three states TanStack Query exposes:
`pending` (skeleton/spinner), `error` (message + retry), `success` (data). Shipping
only the happy state is the ARC-ERRORS/UX-FORMS violation this rule exists to stop.

### STK-VITE-06 — Routes SHOULD be code-split

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Each route component loads via `React.lazy(() => import(...))` under a `Suspense`
fallback, so the first paint pays for one route, not the app. Vite handles chunking
from the dynamic import automatically; the Lighthouse budget (`lighthouserc.json`,
OPS-PERF) is the backstop that notices when a bundle regresses.

### STK-VITE-07 — Nothing secret MUST ever cross the `VITE_` prefix

**Tiers**: all required — **Layer**: G

Vite statically replaces `import.meta.env.VITE_*` in the client bundle — public by
definition, exactly the `NEXT_PUBLIC_` rule (SEC-SECRETS-03). A SPA has no server
side to hide anything in: any call requiring a credential goes through the backing
API, which holds the secret. The grep gate catches secret-shaped `VITE_` names;
the value's sensitivity decides, not the name.

### STK-VITE-08 — Gates MUST run via the scripts contract; tests assert behavior, not implementation

**Tiers**: all required — **Layer**: G

`scripts/lint.sh` = `prettier --check` + `eslint` + `tsc --noEmit` (strict per
STK-TS); `scripts/test.sh` = vitest + Testing Library with coverage
(`--passWithNoTests` keeps a fresh scaffold green). Tests interact the way a user
does — `getByRole`, `getByLabelText`, `userEvent` — and assert visible outcomes.
Asserting on state internals, mock call counts as the primary assertion, or default
snapshots couples tests to refactors instead of behavior.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `scripts/lint.sh` | exit 0 — prettier + eslint + `tsc --noEmit` | STK-VITE-08 |
| 2 | `scripts/test.sh` | exit 0 — vitest green, coverage emitted | STK-VITE-08 |
| 3 | `! git grep … VITE_*(SECRET\|TOKEN\|…)` | exit 0 — no secret-shaped public var | STK-VITE-07 |
| 4-9 | attestation checklist (one per rule) | explicit yes | STK-VITE-01…06 |

**Remediation:** VITE_ grep hit → move the call behind the backing API; rotate the
value if it ever shipped (SEC-SECRETS-05) · flaky Testing Library test → `findBy*` /
`await userEvent`, never `act()` gymnastics or timeouts · "no QueryClient set" in
tests → wrap the render in a fresh `QueryClientProvider` per test.

## Worked Example

`examples/vite-react/` is the living example — two routes, a TanStack Query read, a
react-hook-form + zod form, route error boundary, Testing Library tests:

```
examples/vite-react/
├── index.html
├── src/main.tsx            # QueryClientProvider + RouterProvider
├── src/router.tsx          # createBrowserRouter, React.lazy routes, errorElement
├── src/routes/home.tsx     # useQuery: three states rendered (STK-VITE-02, -05)
├── src/routes/settings.tsx # react-hook-form + zodResolver (STK-VITE-04)
├── src/api.ts              # the app's single server-state access module
├── tests/routes.test.tsx   # behavior via getByRole/userEvent (STK-VITE-08)
└── scripts/{lint.sh,test.sh}
```

```tsx
// src/routes/home.tsx — the three-state rule in one component
const { data, status, refetch } = useQuery({ queryKey: ["todos"], queryFn: fetchTodos });
if (status === "pending") return <p role="status">Loading…</p>;
if (status === "error") return <button onClick={() => refetch()}>Retry</button>;
return <ul>{data.map((t) => <li key={t.id}>{t.title}</li>)}</ul>;
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `useEffect(() => { fetch(...).then(setData) }, [])` | No cache/retry/dedupe; unmount races; per-component loading logic | `useQuery` (STK-VITE-02) |
| Copying query data into `useState` "to edit it" | Two sources of truth drift instantly | Render from query data; mutate via `useMutation` + invalidate |
| Public marketing site as a SPA | Blank-page SEO, JS-gated content, slow first paint | STK-NEXT or STK-HTMX (STK-VITE-01) |
| Selected record / filters in component state | Refresh and deep links lose context | URL params / search params (STK-VITE-03) |
| Hand-rolled `onChange` validation per field | Diverges from submit payload; misses cross-field rules | One zod schema + `zodResolver` (STK-VITE-04) |
| Only the happy path rendered | First API error = white screen | Three states + route `errorElement` (STK-VITE-05) |
| Testing hook internals / mock call counts | Refactors break green tests; behavior regressions pass | Testing Library user-facing queries (STK-VITE-08) |
| `VITE_API_SECRET=` in `.env` | Bundled into public JS | Backing API holds the secret (STK-VITE-07) |

## References

- TanStack Query docs, "Does this replace client state?" — the server-state/UI-state
  split behind STK-VITE-02.
- react-router docs (data routers, `errorElement`) — mechanism for STK-VITE-03/-05.
- Testing Library guiding principles ("the more your tests resemble the way your
  software is used…") — the behavior-not-implementation bar in STK-VITE-08.
- Vite docs, env variables and modes — `VITE_` inlining semantics behind STK-VITE-07.

## Changelog

- **1.0.1** (2026-07-22) — Selection fix: `stacks` narrowed to this standard's own key so auxiliary keys (web/typescript/aws) don't cross-select it into unrelated projects (Phase-4 budget test finding).

- **1.0.0** (2026-07-22) — Initial version.
