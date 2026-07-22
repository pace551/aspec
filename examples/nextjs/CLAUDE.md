# CLAUDE.md — guestbook-example (examples/nextjs)

Worked example for STK-NEXT: one server-component page, one zod-validated server
action, a single "use client" leaf, vitest units, Playwright smoke, standalone output.

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
guestbook-example/
├── app/layout.tsx          # Metadata API template + next/font (STK-NEXT-05, -06)
├── app/page.tsx            # server component: reads the store, renders the form
├── app/actions.ts          # "use server" + zod safeParse (STK-NEXT-03)
├── app/guest-form.tsx      # the ONLY client component (STK-NEXT-02)
├── lib/store.ts            # in-memory store on globalThis (see Gotchas)
├── tests/unit/actions.test.ts   # action as a plain function; next/cache mocked
├── tests/e2e/smoke.spec.ts      # Playwright: build → standalone serve → interact
├── next.config.ts          # output: "standalone" (STK-NEXT-09)
└── scripts/{lint.sh,test.sh}    # the scripts contract
```

## Commands

All commands runnable verbatim from repo root:

```bash
scripts/lint.sh        # prettier --check + eslint + tsc --noEmit (STK-NEXT-07)
scripts/test.sh        # vitest + coverage (STK-NEXT-08)
npx playwright test    # T3+ smoke; builds and serves the standalone output itself
npm run dev            # run the thing (http://localhost:3000)
```

First-time setup: `npm install` (and `npx playwright install chromium` for the smoke).

## Gotchas

- `next start` refuses `output: "standalone"` builds — serve them like a container
  would: `node .next/standalone/server.js` after copying `.next/static` in. The
  Playwright webServer command does exactly that.
- `lib/store.ts` anchors state on `globalThis`: Next keeps separate server module
  graphs (RSC render vs action execution), so plain module state can exist twice.
  A real database makes this moot — do not grow the in-memory store.
- Unit tests mock `next/cache` (`revalidatePath` needs a request scope vitest
  doesn't have). Test actions as functions; test rendering via the smoke.
