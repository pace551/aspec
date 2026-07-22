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
└── scripts/{lint.sh,test.sh}              # the scripts contract
```

## Commands

All commands runnable verbatim from repo root:

```bash
scripts/lint.sh        # swiftformat/swiftlint when installed; degrades with warning
scripts/test.sh        # delegates to checks/stk-swift-verify.sh -> swift test
swift build            # build the library
```

## Gotchas

- Command Line Tools alone can `swift build` this package but NOT `swift test`: the
  XCTest/Testing modules ship with Xcode, not CLT. `stk-swift-verify.sh` detects this
  and degrades with a documented warning instead of failing (STK-SWIFT-06) — install
  Xcode to run the suite for real.
- No hosted CI for this stack by design; verification is the local script.
- A SwiftUI view consumes the model as `@State private var model = CounterModel()` —
  no `@StateObject`/`ObservableObject` (STK-SWIFT-02).
