---
id: STK-TS
title: TypeScript/Node Stack
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [typescript]
triggers:
  - typescript
  - node
  - npm
  - tsconfig
  - vitest
  - eslint
  - prettier
  - zod
  - esm
  - package.json
requires: [SEC-SECRETS]
verification:
  - cmd: "node_modules/.bin/prettier --check ."
    expect: "exit 0"
    layer: G
    rules: [STK-TS-03]
  - cmd: "node_modules/.bin/eslint ."
    expect: "exit 0"
    layer: G
    rules: [STK-TS-03]
  - cmd: "node_modules/.bin/tsc --noEmit"
    expect: "exit 0"
    layer: G
    rules: [STK-TS-02]
  - cmd: "sh -c 'grep -q \"\\\"strict\\\": true\" tsconfig.json && grep -q \"\\\"noUncheckedIndexedAccess\\\": true\" tsconfig.json'"
    expect: "exit 0 — non-negotiable compiler flags present verbatim"
    layer: G
    rules: [STK-TS-02]
  - cmd: "sh -c 'grep -q \"\\\"type\\\": \\\"module\\\"\" package.json && test -f .nvmrc'"
    expect: "exit 0 — ESM declared and Node version pinned"
    layer: G
    rules: [STK-TS-01]
  - cmd: "node_modules/.bin/vitest run --coverage --passWithNoTests"
    expect: "exit 0 — tests green (--passWithNoTests tolerates a fresh scaffold; TST-POLICY governs test existence)"
    layer: G
    rules: [STK-TS-04]
  - cmd: "sh -c 'node_modules/.bin/vitest run --coverage --passWithNoTests >/dev/null 2>&1; python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py --check'"
    expect: "coverage ≥ committed .coverage-baseline (read-only check)"
    layer: G
    rules: [STK-TS-04]
    tiers: [T2, T3, T4]
  - cmd: "sh -c 'test -f package-lock.json && ! git check-ignore -q package-lock.json'"
    expect: "exit 0 — lockfile exists and is not gitignored"
    layer: G
    rules: [STK-TS-05]
  - cmd: "sh -c '[ ! -f package-lock.json ] || npm audit --omit=dev --audit-level=high'"
    expect: "exit 0 (per-advisory waivers handled by /verify-compliance)"
    layer: G
    rules: [STK-TS-05]
    tiers: [T2, T3, T4]
  - cmd: "attest: every external input (CLI args beyond commander, env, file, HTTP, LLM output) crosses a zod schema before use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-TS-06]
  - cmd: "attest: canonical-library table consulted for any new dependency"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-TS-07]
  - cmd: "attest: all documented commands use node_modules/.bin or npm-script paths, never globally installed tools"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-TS-08]
last_review: 2026-07-22
---

# TypeScript/Node Stack (STK-TS)

## Abstract

House rules for every TypeScript/Node project: Node LTS pinned via `.nvmrc`, ESM only,
`tsc --noEmit` under non-negotiable strict flags, eslint (flat config) + prettier as the
lint/format pair, vitest with the coverage ratchet, npm with a committed lockfile, zod
validation at every boundary. Identical toolchain at every tier — tier scales test depth
and CI, not tool choice. Scaffold: `templates/scaffolds/typescript/` · CI:
`templates/ci/typescript.yml` · worked example: `examples/typescript/`.

## Normative Rules

### STK-TS-01 — Projects MUST be ESM-only on a pinned Node LTS

**Tiers**: all required — **Layer**: G

`package.json` declares `"type": "module"`; no CommonJS (`require`, `module.exports`) in
project code, no dual-format builds unless publishing a library that demonstrably needs
them. `.nvmrc` pins the Node major (current LTS line; today `24`) and `engines.node`
states the floor. Runtime code uses `node:`-prefixed builtin imports (`node:fs`,
`node:path`). Local `.env` loading uses `node --env-file=.env`, not a dotenv dependency.

### STK-TS-02 — TypeScript strict mode is non-negotiable and `tsc --noEmit` MUST pass

**Tiers**: all required — **Layer**: G

`tsconfig.json` sets `"strict": true` and `"noUncheckedIndexedAccess": true` — these two
are never disabled, per-file or globally; a codebase that "needs" them off needs fixing,
not configuring. House baseline also sets `module`/`moduleResolution` `NodeNext` and
`verbatimModuleSyntax`. `any` appears only as `unknown`-then-narrow or with an inline
comment justifying it; `@ts-expect-error` (never `@ts-ignore`) requires a trailing reason.
`tsc --noEmit` is the typecheck gate; runtime execution in dev uses `tsx` (no compile
step), production runs compiled `dist/` output.

### STK-TS-03 — eslint (flat config) + prettier MUST pass; that pair is the house default

**Tiers**: all required — **Layer**: G

House choice is eslint flat config with `typescript-eslint` type-checked rules, plus
prettier for formatting (`eslint-config-prettier` disables conflicts). Chosen over biome
deliberately: biome is faster but cannot run type-aware rules (`no-floating-promises`,
`no-misused-promises`), which are the highest-signal lints in a strict async codebase —
one slower tool that catches real bugs beats one fast tool that can't. Suppressions are
inline `// eslint-disable-next-line <rule> -- reason`, never blanket `rules: off` blocks
added to make CI green. `scripts/lint.sh` runs prettier `--check` then eslint.

### STK-TS-04 — Tests MUST run via vitest and coverage MUST never drop below the committed baseline

**Tiers**: all required — **Layer**: G

`vitest` is the only runner (no jest, no node:test mixing). Coverage uses
`@vitest/coverage-v8` with the `json-summary` reporter so
`coverage/coverage-summary.json` feeds `checks/coverage-ratchet.py`; the committed
`.coverage-baseline` only moves up. "Vitest green" is required at every tier; the ratchet
runs at T2+ (see tier-scoped verification entries). Test files live in `tests/` (or
`*.test.ts` beside sources — pick one per repo).

### STK-TS-05 — npm is the house package manager and `package-lock.json` MUST be committed

**Tiers**: all required — **Layer**: G

npm is the boring default — ships with Node, zero extra install, lockfile v3 is
reproducible; pnpm/yarn/bun need a per-repo reason recorded in `GOVERNANCE.md`. CI
installs with `npm ci`, never `npm install`. `npm audit --omit=dev --audit-level=high`
must be clean at T2+; findings are fixed by upgrade or waived per-advisory in
`GOVERNANCE.md` with an unreachability argument and expiry (cadence in `DEV-DEPS`).

### STK-TS-06 — External input MUST cross a zod schema before use

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Anything entering from outside the type system — env vars, file/JSON contents, HTTP
request/response bodies, queue messages, LLM output — is parsed with `zod`
(`schema.parse` / `safeParse`) at the boundary, then flows inward as inferred types
(`z.infer`). No `as MyType` casts on raw external data, no hand-rolled
`typeof x.field === "string"` ladders. A single `config.ts` zod-validates `process.env`
once at startup so missing config fails loudly at boot, not mid-request.

### STK-TS-07 — New dependencies SHOULD come from the canonical-libraries table

**Tiers**: all advisory — **Layer**: A (attestation)

| Need | Use | Not | Why |
|---|---|---|---|
| HTTP client | builtin `fetch` (undici) | `axios`, `node-fetch`, `request` | in the runtime; one less supply-chain edge |
| Validation/models | `zod` | `joi`, hand-rolled checks | typed inference, fails loudly at the boundary (STK-TS-06) |
| CLI | `commander` | `yargs`, raw `process.argv` | one idiom per repo; mirrors argparse role in STK-PY |
| Logging | `pino` | `winston`, `console.log` in services | structured JSON, `OPS-OBS` house logger |
| Dates | `Temporal` where available, else `date-fns` | `moment`, `dayjs` sprawl | moment is dead; Temporal is the stdlib endgame |
| Testing | `vitest` + `@vitest/coverage-v8` | `jest` | ESM-native, no transform config debt |
| Dev runner | `tsx` | `ts-node`, nodemon+build loops | fast ESM TS execution, zero config |
| Env/config | `node --env-file` + zod config module | `dotenv` + scattered `process.env` reads | builtin loading, validated once |

Deviating is fine with a reason (that's SHOULD) — the point is the choice is made once,
here, not re-litigated per session.

### STK-TS-08 — Tools MUST be invoked via `node_modules/.bin` or npm scripts, never global installs

**Tiers**: all required — **Layer**: A (attestation; enforced socially by scaffold + CLAUDE.md)

Every command in docs, CI, scripts, and hooks is `node_modules/.bin/vitest`,
`node_modules/.bin/tsc`, or an `npm run` script — never a globally installed `tsc`/
`eslint` whose version drifts from the lockfile (the same failure class STK-PY-08 retires
for venvs). `npx` is acceptable only for one-off scaffolding commands, not for anything a
gate depends on.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `node_modules/.bin/prettier --check .` | exit 0 | STK-TS-03 |
| 2 | `node_modules/.bin/eslint .` | exit 0 | STK-TS-03 |
| 3 | `node_modules/.bin/tsc --noEmit` | exit 0 | STK-TS-02 |
| 4 | grep `strict` + `noUncheckedIndexedAccess` in tsconfig.json | both present | STK-TS-02 |
| 5 | grep `"type": "module"` + `.nvmrc` exists | exit 0 | STK-TS-01 |
| 6 | `vitest run --coverage --passWithNoTests` | exit 0 | STK-TS-04 |
| 7 | vitest coverage → `coverage-ratchet.py --check` (T2+) | ≥ `.coverage-baseline` | STK-TS-04 |
| 8 | lockfile exists and not gitignored | exit 0 | STK-TS-05 |
| 9 | `npm audit --omit=dev --audit-level=high` (T2+) | exit 0 / per-advisory waivers | STK-TS-05 |
| 10-12 | attestation checklist (one per rule) | explicit yes | STK-TS-06, -07, -08 |

**Remediation:** prettier fail → `node_modules/.bin/prettier --write .` · eslint
type-aware rule fires on a promise → `await` it or `void` it with a comment · `tsc` errors
after enabling `noUncheckedIndexedAccess` → handle the `undefined` (that's the bug it
found) · `npm audit` hit → `npm audit fix` / upgrade first; waive per-advisory only with
unreachability argument · ratchet fail → add tests for the new code, don't lower the
baseline.

## Worked Example

`examples/typescript/` is the living example (a zod-validated NDJSON tally CLI). Minimal
shape:

```
myproj/
├── package.json            # "type": "module", engines, npm scripts
├── package-lock.json       # committed (STK-TS-05)
├── .nvmrc                  # 24
├── tsconfig.json           # strict + noUncheckedIndexedAccess, NodeNext
├── eslint.config.js        # flat config, typescript-eslint type-checked + prettier
├── vitest.config.ts        # coverage: v8, reporter json-summary
├── .coverage-baseline      # written by first ratchet run, committed
├── .env.example            # per SEC-SECRETS
├── src/cli.ts              # commander entry; tsx src/cli.ts in dev
├── src/schema.ts           # zod at the boundary (STK-TS-06)
└── tests/tally.test.ts
```

```jsonc
// tsconfig.json (house baseline)
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2023",
    "verbatimModuleSyntax": true,
    "outDir": "dist",
    "skipLibCheck": true
  }
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `as MyType` on parsed JSON | Type lie; runtime shape unchecked | `schema.parse(json)` with zod (STK-TS-06) |
| `@ts-ignore` to silence an error | Hides the next error on that line too | `@ts-expect-error -- reason` (self-expiring) |
| Loosening tsconfig to unblock a lib | Punishes the whole codebase for one dep | Narrow wrapper module with local justification |
| Mixing CJS `require` into ESM | Dual-mode resolution bugs, broken tree-shaking | ESM only (STK-TS-01) |
| Global `npm install -g typescript` in docs/CI | Version drifts from lockfile | `node_modules/.bin/tsc` (STK-TS-08) |
| `npm install` in CI | Mutates lockfile, non-reproducible builds | `npm ci` (STK-TS-05) |
| Floating promise (`doAsync()` unawaited) | Swallowed rejections crash later or never | type-aware eslint rule; `await`/`void` explicitly |
| `console.log` logging in a service | Unstructured, unlevelled, unparseable | `pino` (STK-TS-07, OPS-OBS) |

## References

- typescript-eslint docs (type-checked configs) — the reason eslint+prettier beat biome
  as house default (STK-TS-03).
- Node.js releases page — LTS schedule behind the `.nvmrc` pin (STK-TS-01).
- zod v3+ docs — boundary-parsing idiom and `z.infer` flow (STK-TS-06).
- vitest coverage docs — `json-summary` reporter is what the ratchet consumes (STK-TS-04).
- npm `ci` docs — reproducible-install contract behind STK-TS-05.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
