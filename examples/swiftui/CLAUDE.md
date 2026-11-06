# CLAUDE.md — CounterKit (examples/swiftui)

Worked example for STK-SWIFT: an SPM library with an `@Observable` model (Observation
framework) and Swift Testing tests — the MV testable-core pattern, no UI target needed.

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
CounterKit/
├── Package.swift                          # swift-tools 6.0; macOS 14 / iOS 17 targets
├── Sources/CounterKit/CounterModel.swift  # @Observable model; deps via init (STK-SWIFT-05)
├── Tests/CounterKitTests/CounterModelTests.swift  # Swift Testing (@Test/#expect)
└── scripts/                               # the scripts contract: lint.sh, test.sh
                                           # (+ coverage.sh), lockfile-check.py, sca.sh,
                                           # license-audit.py
```

## Commands

All commands runnable verbatim from repo root:

```bash
scripts/lint.sh        # swiftformat + swiftlint when installed; degrades with warning
scripts/test.sh        # full Xcode: tests + lcov.info (coverage.sh); else stk-swift-verify.sh
swift build            # build the library
python3 scripts/lockfile-check.py   # resolved pins match the committed Package.resolved
scripts/sca.sh                      # osv-scanner on SwiftPM lockfiles
python3 scripts/license-audit.py    # every pin reviewed in licenses.allow
```

## Gotchas

- Command Line Tools alone can `swift build` this package but NOT `swift test`: the
  XCTest/Testing modules ship with Xcode, not CLT. `stk-swift-verify.sh` detects this
  and degrades with a documented warning instead of failing (STK-SWIFT-06) — install
  Xcode to run the suite for real.
- Hosted CI is `templates/ci/swiftui.yml` for public repositories (macOS runners and
  CodeQL are free there); ASPEC's own `swiftui-template` workflow runs these scripts on
  this example. On a private repo it's a spend decision (C6), so verification stays the
  local scripts.
- A SwiftUI view consumes the model as `@State private var model = CounterModel()` —
  no `@StateObject`/`ObservableObject` (STK-SWIFT-02).
