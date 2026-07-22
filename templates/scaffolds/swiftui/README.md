# Scaffold: swiftui (SPM package) — STK-SWIFT

An SPM package template testable via `swift test` (Command Line Tools are enough — no
Xcode required). `/bootstrap-repo` copies it, renames the `MyPackage` module and
directories to the project name, and merges `_common/` (gitignore-base, `.env.example`,
`CLAUDE.md`, `GOVERNANCE.md`, git hooks).

Deliberate trim (STK-SWIFT-06): this stack has **no hosted CI workflow**. Verification
is local: `checks/stk-swift-verify.sh` runs `swift test` here (or `xcodebuild test` for
app projects), degrading with a documented warning when the toolchain is absent.

Scripts contract:

- `scripts/lint.sh` — `swiftformat --lint` / `swiftlint` when installed; degrades with a
  documented warning otherwise (never a silent pass)
- `scripts/test.sh` — delegates to `stk-swift-verify.sh` (falls back to plain
  `swift test` if the governance repo is not present)

Shape (MV per STK-SWIFT-05): logic lives in `@Observable` models under `Sources/`,
constructed with their dependencies and tested without UI. An app target grows around
this package later — the package stays the testable core.
