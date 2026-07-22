# CLAUDE.md — statusboard-example (examples/vite-react)

Worked example for STK-VITE: an internal-dashboard SPA — TanStack Query server state,
react-router with lazy routes and a route error boundary, react-hook-form + zod, and
Testing Library tests that assert behavior.

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
statusboard-example/
├── index.html
├── src/main.tsx            # QueryClientProvider + RouterProvider
├── src/router.tsx          # createBrowserRouter; React.lazy routes; errorElement
├── src/api.ts              # the single server-state access module (STK-VITE-02)
├── src/routes/home.tsx     # useQuery with all three states (STK-VITE-05)
├── src/routes/settings.tsx # react-hook-form + zodResolver + useMutation (STK-VITE-04)
├── tests/routes.test.tsx   # getByRole/userEvent behavior tests (STK-VITE-08)
└── scripts/{lint.sh,test.sh}    # the scripts contract
```

## Commands

All commands runnable verbatim from repo root:

```bash
scripts/lint.sh        # prettier --check + eslint + tsc --noEmit
scripts/test.sh        # vitest + Testing Library + coverage
npm run build          # tsc-checked production build (code-split per route)
npm run dev            # run the thing (http://localhost:5173)
```

First-time setup: `npm install`

## Gotchas

- `src/api.ts` fakes latency in place of a real backend; swap function bodies for
  `fetch()` calls — components never change (that's the point of STK-VITE-02).
- Tests render route components directly inside a fresh `QueryClientProvider` per
  test (retries off). RTL auto-cleanup is wired in `tests/setup.ts` because vitest
  globals are disabled.
- `dist/assets` shows one chunk per route (home/settings) — that's STK-VITE-06
  working; if a route stops having its own chunk, someone broke the lazy import.
