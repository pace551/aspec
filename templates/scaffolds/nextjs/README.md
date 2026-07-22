# Scaffold: nextjs — STK-NEXT

Copied into a new project by `/bootstrap-repo`, which also:

- fills `{{PROJECT_NAME}}` in `package.json` and `app/layout.tsx`,
- merges `_common/` (gitignore-base, `.env.example`, `CLAUDE.md`, `GOVERNANCE.md`, git hooks),
- runs `npm install` (and `npx playwright install chromium` at T3+).

Scripts contract (hooks, CI, and /verify-compliance all run these):

- `scripts/lint.sh` — prettier --check + eslint + `tsc --noEmit` (STK-NEXT-07)
- `scripts/test.sh` — vitest + coverage, `--passWithNoTests` (STK-NEXT-08)

Baked-in decisions (see `standards/stacks/stk-next.md`):

- App Router only; server components by default — `"use client"` goes on interaction
  leaves you add, never on pages/layouts (STK-NEXT-01/-02)
- server actions validate with zod before use (STK-NEXT-03; see `examples/nextjs/`)
- `output: "standalone"` in `next.config.ts`; the Playwright webServer serves the
  standalone build the way a container would (STK-NEXT-09)
- `lighthouserc.json` seeds the OPS-PERF budget the CI lighthouse job asserts
