# Scaffold: typescript (STK-TS)

Copied by `/bootstrap-repo` for new TypeScript/Node projects. On copy, bootstrap:

1. Fills `{{PROJECT_NAME}}` / `{{ONE_LINE_DESCRIPTION}}` in `package.json` and
   `src/index.ts`.
2. Layers in `_common/` (CLAUDE.md.seed → `CLAUDE.md`, GOVERNANCE.md.seed →
   `GOVERNANCE.md`, appends `gitignore-base` to `.gitignore`, installs git hooks via
   `install-git-hooks.sh`).
3. Installs: `npm install` (creates `package-lock.json` — commit it, STK-TS-05).

Scripts contract (`_common/README.md`): hooks, CI (`templates/ci/typescript.yml`), and
`/verify-compliance` all run `scripts/lint.sh` and `scripts/test.sh`. Tools by
`node_modules/.bin` path, never global installs (STK-TS-08). Add `zod` as a dependency
the moment the project has an external boundary (STK-TS-06).

Worked example built from this scaffold: `examples/typescript/`.
