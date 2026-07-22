# CLAUDE.md — tally-example

NDJSON event tally CLI. Worked example for STK-TS: strict TypeScript, ESM only, zod at
the boundary, commander CLI, vitest coverage feeding the ratchet.

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
examples/typescript/
├── package.json + package-lock.json   # npm, lockfile committed (STK-TS-05)
├── tsconfig.json                      # strict + noUncheckedIndexedAccess (STK-TS-02)
├── eslint.config.js                   # flat config, type-checked rules + prettier
├── vitest.config.ts                   # coverage json-summary for the ratchet
├── src/
│   ├── schema.ts                      # zod boundary: NDJSON → typed Events (STK-TS-06)
│   ├── tally.ts                       # pure grouping/sorting logic
│   ├── cli.ts                         # commander wiring, injectable Io
│   └── main.ts                        # thin binary entry
└── tests/                             # schema / tally / cli e2e tests
```

## Commands

All commands runnable verbatim from repo root (node_modules/.bin paths — STK-TS-08):

```bash
scripts/lint.sh                                  # prettier --check + eslint (same gate as hook and CI)
scripts/test.sh                                  # vitest + coverage-summary.json (same gate as hook and CI)
node_modules/.bin/tsc --noEmit                   # typecheck
node_modules/.bin/tsx src/main.ts events.ndjson  # run the thing (--field event|user)
```

Setup once: `npm install` (CI uses `npm ci`).

## Gotchas

- `main.ts` shows 0% coverage by design (it's the process-global shim); logic lives in
  `run()` which the e2e tests cover. Don't move logic into `main.ts`.
- `noUncheckedIndexedAccess` makes `lines[i]` `string | undefined` — handle the
  undefined; do not "fix" with `!`.
