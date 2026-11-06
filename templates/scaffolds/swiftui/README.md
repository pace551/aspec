# Scaffold: swiftui (SPM package) — STK-SWIFT

An SPM package template testable via `swift test` (Command Line Tools are enough — no
Xcode required). `/bootstrap-repo` copies it, renames the `MyPackage` module and
directories to the project name, and merges `_common/` (gitignore-base, `.env.example`,
`CLAUDE.md`, `GOVERNANCE.md`, git hooks).

Verification is local by default (STK-SWIFT-06): `checks/stk-swift-verify.sh` runs
`swift test` here (or `xcodebuild test` for app projects), degrading with a documented
warning when the toolchain is absent. Hosted CI is `templates/ci/swiftui.yml`, for public
repositories: GitHub's standard macOS runners and CodeQL are free there. On a private
repo they cost money, so adopting it is a spend decision (C6).

Scripts contract:

- `scripts/lint.sh` — `swiftformat --lint` / `swiftlint` when installed; degrades with a
  documented warning otherwise (never a silent pass)
- `scripts/test.sh` — for this package with full Xcode, runs `scripts/coverage.sh`
  (tests with coverage, exported as `lcov.info` for the ratchet; gitignored). Otherwise
  it delegates to `stk-swift-verify.sh`: `xcodebuild test` for an app project, or a
  warning where Command Line Tools can't run tests (plain `swift test` without the
  governance repo)
- `scripts/lockfile-check.py` — whatever `swift package resolve` pins must match the
  committed `Package.resolved` (SEC-SUPPLY-02)
- `scripts/sca.sh` — osv-scanner on every SwiftPM lockfile, Xcode's included
  (SEC-SUPPLY-01)
- `scripts/license-audit.py` — LEG-LICENSING-01: every pinned dependency needs a reviewed
  `<location> <version> <SPDX id>` line in `licenses.allow` (its repository URL) naming
  an allowed license, so a new version or a fork is reviewed again

Shape (MV per STK-SWIFT-05): logic lives in `@Observable` models under `Sources/`,
constructed with their dependencies and tested without UI. An app target grows around
this package later — the package stays the testable core.
