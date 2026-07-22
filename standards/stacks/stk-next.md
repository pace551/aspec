---
id: STK-NEXT
title: Next.js Stack
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [nextjs, typescript, web]
triggers:
  - nextjs
  - next.js
  - app router
  - server component
  - server action
  - react
  - ssr
  - vercel
  - next/image
requires: [STK-TS]
verification:
  - cmd: "scripts/lint.sh"
    expect: "exit 0 — prettier --check + eslint + tsc --noEmit (strict), same gate as pre-commit hook and CI"
    layer: G
    rules: [STK-NEXT-07]
  - cmd: "scripts/test.sh"
    expect: "exit 0 — vitest green with coverage emitted (--passWithNoTests tolerates a fresh scaffold)"
    layer: G
    rules: [STK-NEXT-08]
  - cmd: "sh -c 'npx playwright test --reporter=line'"
    expect: "exit 0 — smoke spec passes against the built app (browsers via `npx playwright install chromium`)"
    layer: G
    rules: [STK-NEXT-08]
    tiers: [T3, T4]
  - cmd: "sh -c '! git grep --untracked -InE \"NEXT_PUBLIC_[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PRIVATE|API_KEY|ACCESS_KEY|CREDENTIAL)\" 2>/dev/null'"
    expect: "exit 0 — no secret-shaped name behind the NEXT_PUBLIC_ prefix anywhere in the tree"
    layer: G
    rules: [STK-NEXT-04]
  - cmd: "sh -c '! git grep --untracked -InE \"<img[ >]\" -- \"*.tsx\" \"*.jsx\" 2>/dev/null'"
    expect: "exit 0 — no raw <img> in components; use next/image"
    layer: G
    rules: [STK-NEXT-06]
    tiers: [T3, T4]
  - cmd: "attest: routing is App Router only — no pages/ directory, no mixed-router state"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-NEXT-01]
  - cmd: "attest: components are server components by default; every \"use client\" sits at an interaction leaf"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-NEXT-02]
  - cmd: "attest: every server action and route handler parses its input through a zod schema before use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-NEXT-03]
  - cmd: "attest: every routable page resolves metadata via the Metadata API (root layout template + per-page overrides)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-NEXT-05]
  - cmd: "attest: container deploys build with output standalone; the image never contains node_modules wholesale"
    expect: "explicit yes in GOVERNANCE.md attestations (n/a when deploying to Vercel)"
    layer: A
    rules: [STK-NEXT-09]
last_review: 2026-07-22
---

# Next.js Stack (STK-NEXT)

## Abstract

House rules for Next.js applications: App Router only, server components by default with
`"use client"` pushed to interaction leaves, zod validation on every server action and
route handler, nothing secret behind `NEXT_PUBLIC_`, the Metadata API for SEO,
`next/image`/`next/font` for performance, strict TypeScript per STK-TS, vitest for units
plus a Playwright smoke at T3+, and standalone output when self-hosting containers. The
toolchain is identical at every tier; what scales with tier is gate depth (a11y,
Lighthouse, e2e land at T3). Scaffold: `templates/scaffolds/nextjs/` · CI:
`templates/ci/nextjs.yml` · worked example: `examples/nextjs/`.

## Normative Rules

### STK-NEXT-01 — The App Router MUST be the only routing system

**Tiers**: all required — **Layer**: A (attestation; structure is set once at bootstrap)

All routes live under `app/` (layouts, pages, route handlers, server actions). No
`pages/` directory, no mixed-router migration state in new projects — half-migrated
apps pay both mental models forever. Route handlers (`app/**/route.ts`) exist only for
genuine machine consumers (webhooks, feeds); UI mutations go through server actions.

### STK-NEXT-02 — Components MUST be server components by default; `"use client"` only at interaction leaves

**Tiers**: all required — **Layer**: A (attestation)

Pages, layouts, and data display render on the server: fetch where the data is used,
no client waterfall. `"use client"` marks the smallest component that actually needs
state, effects, or event handlers (a form, a toggle, a chart) — never a page or layout
wholesale, since the directive infects the whole subtree. Props crossing the boundary
are serializable; pass data down, not fetch functions.

### STK-NEXT-03 — Server actions and route handlers MUST validate input with zod

**Tiers**: all required — **Layer**: A (attestation)

Every server action and route handler is a public HTTP endpoint regardless of which
form renders it — Next.js generates a callable route for each action. Parse `FormData`
or JSON through a zod schema (`safeParse`) at the top of the function before any use
(SEC-INPUT), and re-check authorization inside the action — never trust hidden fields
or the fact that the UI only shows the button to admins. Return typed field errors so
the form can render its error state (UX-FORMS).

### STK-NEXT-04 — Nothing secret MUST ever cross the `NEXT_PUBLIC_` prefix

**Tiers**: all required — **Layer**: G

`NEXT_PUBLIC_` values are string-inlined into the browser bundle at build time —
public by definition (SEC-SECRETS-03). Secrets stay in unprefixed variables read only
in server code; calls needing a key are proxied through a server action or route
handler. The grep gate catches secret-shaped names; renaming a secret to an innocuous
`NEXT_PUBLIC_` name is a violation of the rule, not a pass of the check — sensitivity
of the value decides, not the name.

### STK-NEXT-05 — Every routable page MUST declare metadata via the Metadata API

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The root layout exports a `metadata` object with a `title.template` and site
description; pages export `metadata` or `generateMetadata` for dynamic titles and
OpenGraph fields on shareable pages. No hand-rolled `<head>` manipulation. What the
content should say is UX-SEO's business; this rule fixes the mechanism.

### STK-NEXT-06 — Images and fonts MUST go through `next/image` and `next/font`

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

Raw `<img>` tags and `<link>`-loaded webfonts are the two classic OPS-PERF budget
killers (layout shift, unoptimized bytes, third-party font requests). `next/image`
gets sizing, lazy loading, and format negotiation; `next/font` self-hosts with zero
layout shift. The grep gate rejects raw `<img` in components; a justified escape hatch
is `next/image` with `unoptimized` plus a comment, not a raw tag.

### STK-NEXT-07 — TypeScript strict and lint gates MUST pass via `scripts/lint.sh`

**Tiers**: all required — **Layer**: G

`tsconfig.json` has `"strict": true` per STK-TS — no per-file opt-outs to make errors
disappear. `scripts/lint.sh` runs `prettier --check`, `eslint` (with
`eslint-config-next` core-web-vitals rules), and `tsc --noEmit`; the pre-commit hook
and the CI lint/typecheck jobs run the same script, so "passing" is defined once.

### STK-NEXT-08 — Tests MUST run via vitest; a Playwright smoke covers the critical path at T3+

**Tiers**: all required — **Layer**: G

`scripts/test.sh` runs vitest with coverage (json-summary for the ratchet);
`--passWithNoTests` keeps a fresh scaffold green until TST-POLICY demands tests.
Server actions are unit-tested as plain async functions — zod rejection paths first,
then the happy path. At T3+ a Playwright smoke (`tests/e2e/`) boots the built app,
loads the key page, and performs one real interaction; it is the "does it actually
serve" gate CI runs before a11y/Lighthouse.

### STK-NEXT-09 — Container deploys SHOULD use `output: "standalone"`

**Tiers**: all advisory — **Layer**: A (attestation)

`output: "standalone"` in `next.config.ts` emits a self-contained `server.js` with
only the traced dependencies — the Dockerfile copies `.next/standalone` +
`.next/static` + `public/`, not the whole `node_modules`. Irrelevant on Vercel;
mandatory practice the moment the app is self-hosted (ECS/Fly/etc.).

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `scripts/lint.sh` | exit 0 — prettier + eslint + `tsc --noEmit` | STK-NEXT-07 |
| 2 | `scripts/test.sh` | exit 0 — vitest green, coverage emitted | STK-NEXT-08 |
| 3 | `npx playwright test --reporter=line` (T3+) | exit 0 — smoke spec green | STK-NEXT-08 |
| 4 | `! git grep … NEXT_PUBLIC_*(SECRET\|TOKEN\|…)` | exit 0 — no secret-shaped public var | STK-NEXT-04 |
| 5 | `! git grep … "<img[ >]"` in tsx/jsx (T3+) | exit 0 — no raw `<img>` | STK-NEXT-06 |
| 6-10 | attestation checklist (one per rule) | explicit yes | STK-NEXT-01, -02, -03, -05, -09 |

**Remediation:** `tsc` errors after a dependency bump → fix types, never loosen
`strict` · playwright "browser not found" → `npx playwright install chromium` ·
NEXT_PUBLIC grep hit → move the var server-side and proxy the call through a server
action; rotate the value if it ever shipped (SEC-SECRETS-05) · raw `<img>` hit →
`next/image` with explicit `width`/`height`.

## Worked Example

`examples/nextjs/` is the living example — one server-component page, one
zod-validated server action, vitest units, playwright smoke:

```
examples/nextjs/
├── app/layout.tsx          # metadata template + next/font (STK-NEXT-05, -06)
├── app/page.tsx            # server component; renders the form + entries
├── app/actions.ts          # "use server" + zod safeParse (STK-NEXT-03)
├── app/guest-form.tsx      # "use client" leaf: the only client component
├── tests/unit/actions.test.ts
├── tests/e2e/smoke.spec.ts # T3+ gate; present from day one
└── scripts/{lint.sh,test.sh}
```

```ts
// app/actions.ts
"use server";
import { z } from "zod";

const Entry = z.object({ name: z.string().trim().min(1).max(80) });

export async function signGuestbook(_prev: unknown, formData: FormData) {
  const parsed = Entry.safeParse({ name: formData.get("name") });
  if (!parsed.success) return { error: "Name must be 1-80 characters." };
  await save(parsed.data.name);
  return { ok: true };
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `"use client"` at the top of a page/layout | Entire subtree loses server rendering; bundle balloons | Extract the interactive leaf (STK-NEXT-02) |
| Fetching in `useEffect` inside a client component | Client waterfall, no streaming, loading spinners everywhere | Fetch in the server component, pass data down |
| Server action trusting `formData` shapes | Actions are public endpoints; crafted POSTs bypass the UI | zod `safeParse` + authz inside the action (STK-NEXT-03) |
| Secret in a `NEXT_PUBLIC_` var "because the client needs it" | Inlined into public JS forever | Proxy via server action; secret stays server-side (STK-NEXT-04) |
| Route handler + server action for the same mutation | Two public surfaces to validate and authorize | One server action; handlers for machine consumers only |
| `pages/`-era patterns (`getServerSideProps`) in App Router code | Dead API; copy-pasted from stale examples | Async server components + `fetch`/ORM directly |
| Raw `<img>`/`<link>` Google-Fonts tag | CLS + third-party request; fails Lighthouse budget | `next/image`, `next/font` (STK-NEXT-06) |

## References

- Next.js docs, App Router + Data Security (server actions are public endpoints) — the
  threat model behind STK-NEXT-03.
- Next.js docs, environment variables (`NEXT_PUBLIC_` inlining semantics) — mechanism
  behind STK-NEXT-04.
- Next.js docs, `output: "standalone"` + official Docker example — basis for STK-NEXT-09.
- web.dev CLS/LCP guidance — why images and fonts are the perf rules with teeth
  (STK-NEXT-06, enforced via OPS-PERF budgets).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
