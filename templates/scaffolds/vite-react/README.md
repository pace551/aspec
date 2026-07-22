# Scaffold: vite-react (SPA) — STK-VITE

For internal tools and dashboards only — public content sites use the nextjs or htmx
scaffolds (STK-VITE-01). Copied into a new project by `/bootstrap-repo`, which also:

- fills `{{PROJECT_NAME}}` in `package.json` and `index.html`,
- merges `_common/` (gitignore-base, `.env.example`, `CLAUDE.md`, `GOVERNANCE.md`, git hooks),
- runs `npm install`.

Scripts contract (hooks, CI, and /verify-compliance all run these):

- `scripts/lint.sh` — prettier --check + eslint + `tsc --noEmit` (strict per STK-TS)
- `scripts/test.sh` — vitest + Testing Library + coverage, `--passWithNoTests`

Baked-in decisions (see `standards/stacks/stk-vite.md`):

- server state through TanStack Query only — grow `src/api.ts`, never fetch in
  useEffect (STK-VITE-02)
- react-router data router; routes lazy + errorElement from day one (STK-VITE-03/-05/-06)
- forms with react-hook-form + zodResolver (STK-VITE-04; see `examples/vite-react/`)
- nothing secret behind `VITE_` (STK-VITE-07)
- `lighthouserc.json` seeds the OPS-PERF budget the CI lighthouse job asserts
