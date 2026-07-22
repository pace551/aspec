---
id: STK-SWIFT
title: Apple SwiftUI Stack
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [swiftui]
triggers:
  - swift
  - swiftui
  - ios
  - macos
  - xcode
  - spm
  - observable
  - xctest
  - swift testing
  - keychain
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/stk-swift-verify.sh"
    expect: "exit 0 — swift test (SPM) or xcodebuild test (app project) green; degrades to a documented warning when Xcode tooling is absent (rule falls back to attestation)"
    layer: G
    rules: [STK-SWIFT-06]
  - cmd: "sh -c '[ ! -f Podfile ] && [ ! -f Cartfile ]'"
    expect: "exit 0 — no CocoaPods/Carthage manifests; dependencies via SPM only"
    layer: G
    rules: [STK-SWIFT-04]
  - cmd: "sh -c '! git grep --untracked -In \"ObservableObject\" -- \"*.swift\" 2>/dev/null'"
    expect: "exit 0 — no ObservableObject conformances on current targets (waive per-file for legacy deployment targets)"
    layer: G
    rules: [STK-SWIFT-02]
  - cmd: "sh -c '! git grep --untracked -InE \"UserDefaults.*([sS]ecret|[tT]oken|[pP]assword|[aA]pi[_]?[kK]ey|[cC]redential)\" -- \"*.swift\" 2>/dev/null'"
    expect: "exit 0 — no secret-shaped values going through UserDefaults"
    layer: G
    rules: [STK-SWIFT-07]
  - cmd: "attest: UI is SwiftUI; any UIKit/AppKit drop-down is a wrapped leaf with a stated reason"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SWIFT-01]
  - cmd: "attest: concurrency is async/await with structured tasks; legacy callbacks are wrapped once at the boundary"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SWIFT-03]
  - cmd: "attest: views stay small; logic lives in @Observable models constructed with their dependencies and tested without UI"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SWIFT-05]
  - cmd: "attest: every interactive element without a text label carries an accessibilityLabel"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SWIFT-08]
last_review: 2026-07-22
---

# Apple SwiftUI Stack (STK-SWIFT)

## Abstract

Rules for Apple-platform apps and packages: SwiftUI-first with UIKit only by
documented exception, the Observation framework's `@Observable` over
`ObservableObject` on current targets, async/await structured concurrency,
dependencies via Swift Package Manager only, and the MV shape — small views, logic in
observable models testable without UI. Secrets go to Keychain, never UserDefaults;
interactive elements carry accessibility labels. Deliberate trim: no hosted CI for
this stack — verification runs `checks/stk-swift-verify.sh`, which runs `swift test`
or `xcodebuild test` locally and degrades gracefully when Xcode tooling is absent.
Scaffold: `templates/scaffolds/swiftui/` (SPM package) · worked example:
`examples/swiftui/`.

## Normative Rules

### STK-SWIFT-01 — UI MUST be SwiftUI; UIKit/AppKit only by documented exception

**Tiers**: all required — **Layer**: A (attestation)

New screens are SwiftUI. Dropping to UIKit/AppKit is allowed only where SwiftUI
genuinely lacks the capability (an `NSViewRepresentable`/`UIViewRepresentable` leaf
wrapping the specific control), with a one-line reason at the wrapper. Whole UIKit
view controllers hosting SwiftUI fragments is the wrong direction — the host is
SwiftUI, the exception is the leaf.

### STK-SWIFT-02 — Observable models MUST use `@Observable`, not `ObservableObject`, on current targets

**Tiers**: all required — **Layer**: G

Current targets means iOS 17+/macOS 14+ — the house default for new work. The
Observation framework tracks per-property access, so views re-render only on fields
they read; `ObservableObject`/`@Published` invalidates every observer on any change
and drags `Combine` along. No `@StateObject`/`@ObservedObject` in new code — models
enter views as `@State` (owned) or plain `let`/`@Environment` (passed in). Projects
stuck on older deployment targets waive this per-rule with the target as the reason.

### STK-SWIFT-03 — Concurrency MUST be async/await with structured tasks

**Tiers**: all required — **Layer**: A (attestation)

No new completion-handler APIs and no nested-callback pyramids. Legacy callback APIs
get wrapped once at the boundary with `withCheckedThrowingContinuation`; parallel
work uses `async let`/`TaskGroup` so cancellation propagates; UI-touching model
surface is `@MainActor`. `Task.detached` is by exception with a comment — unstructured
tasks escape cancellation and are the async version of a leaked thread.

### STK-SWIFT-04 — Dependencies MUST come via Swift Package Manager only

**Tiers**: all required — **Layer**: G

No CocoaPods, no Carthage — one dependency system, resolvable by `swift build` and
Xcode alike, no workspace mutation, no `pod install` drift. `Package.resolved` is
committed (the lockfile). Keep the dependency count honest: most of what a personal
app needs is in the SDK.

### STK-SWIFT-05 — Views SHOULD stay small; logic lives in observable models (MV)

**Tiers**: all advisory — **Layer**: A (attestation)

The house pattern is MV, not ceremonial MVVM: no one-view-model-per-view rule.
Views declare layout and bind to `@Observable` models; anything with a branch worth
testing (validation, derivation, sequencing) lives in a model that takes its
dependencies through `init` and runs under `swift test` with no UI, no simulator.
When a view's body outgrows a screenful, extract subviews before inventing
abstraction layers.

### STK-SWIFT-06 — Tests MUST run via `checks/stk-swift-verify.sh` (Swift Testing or XCTest)

**Tiers**: all required — **Layer**: G

Swift Testing (`import Testing`, `#expect`) for new code; XCTest remains sanctioned
for UI tests and existing suites. The verify script runs `swift test` when
`Package.swift` exists, else `xcodebuild test` for app projects — and exits 0 with a
loud documented warning when the toolchain can't run tests at all (Command Line Tools
without Xcode ship the compiler but neither the XCTest nor Testing modules, and can't
build app projects), at which point the rule is satisfied only by attestation that
tests ran on a machine that could. Deliberate trim: no hosted CI workflow for this
stack — macOS runners aren't worth the spend at personal scale (C6).

### STK-SWIFT-07 — Secrets MUST live in Keychain, never UserDefaults or source

**Tiers**: all required — **Layer**: G

UserDefaults is a plaintext plist — backed up, unencrypted, trivially readable
(SEC-SECRETS-03's ladder, native rung: Keychain Services). Tokens, passwords, and
API keys go through Keychain (`kSecClass…` or a thin wrapper). A secret that "must
ship in the binary" is a design smell: proxy the privileged call through a backend
you control instead. The grep gate catches secret-shaped UserDefaults usage; the
value's sensitivity decides, not the name.

### STK-SWIFT-08 — Interactive elements MUST carry accessibility labels

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

UX-A11Y applies to native too. Every control whose visual is not text — icon
buttons, gesture targets, custom shapes — gets `.accessibilityLabel` naming the
action ("Delete entry", not "trash icon"), plus `.accessibilityValue`/`Hint` where
state matters. Audit with Accessibility Inspector before calling a T3+ screen done;
VoiceOver reading "button" three times in a row is the failure this rule retires.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/stk-swift-verify.sh` | exit 0 — tests green (or documented degrade → attestation) | STK-SWIFT-06 |
| 2 | `[ ! -f Podfile ] && [ ! -f Cartfile ]` | exit 0 — SPM only | STK-SWIFT-04 |
| 3 | `! git grep … "ObservableObject"` in *.swift | exit 0 — Observation framework in use | STK-SWIFT-02 |
| 4 | `! git grep … UserDefaults secret-pattern` | exit 0 — no secrets in UserDefaults | STK-SWIFT-07 |
| 5-8 | attestation checklist (one per rule) | explicit yes | STK-SWIFT-01, -03, -05, -08 |

**Remediation:** verify script warns "no test frameworks"/"toolchain absent" → run on
a machine with full Xcode and attest, don't skip silently · ObservableObject hit on a current-target
project → migrate: `@Observable` class, drop `@Published`, `@StateObject` → `@State` ·
UserDefaults grep hit → move the value to Keychain and rotate it (SEC-SECRETS-05) ·
`xcodebuild` fails under Command Line Tools → `sudo xcode-select -s /Applications/Xcode.app`.

## Worked Example

`examples/swiftui/` is the living example — an SPM library with an `@Observable`
model and Swift Testing tests, green under `swift test` with no Xcode required:

```
examples/swiftui/
├── Package.swift                    # swift-tools 6.0, macOS 14 target
├── Sources/CounterKit/CounterModel.swift
├── Tests/CounterKitTests/CounterModelTests.swift
└── scripts/{lint.sh,test.sh}        # test.sh delegates to stk-swift-verify.sh
```

```swift
// Sources/CounterKit/CounterModel.swift
import Observation

@Observable
public final class CounterModel {
    public private(set) var count: Int
    public let step: Int
    public init(count: Int = 0, step: Int = 1) { ... }   // deps via init (STK-SWIFT-05)
    public func increment() { count += step }
}

// Tests: Swift Testing, no UI needed
@Test func incrementMovesByStep() {
    let model = CounterModel(step: 5)
    model.increment()
    #expect(model.count == 5)
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `ObservableObject` + `@Published` in new code | Whole-object invalidation; Combine dependency; more boilerplate | `@Observable` (STK-SWIFT-02) |
| Completion-handler pyramids (`load { a in save { b in … } }`) | Unreadable, cancellation-blind, error paths forgotten | async/await + structured tasks (STK-SWIFT-03) |
| One ViewModel class per view, always | Ceremony without benefit; indirection for static screens | MV: model only where logic exists (STK-SWIFT-05) |
| Business logic inside `View.body` / `Button` closures | Untestable without UI automation | Move to an `@Observable` model method |
| `UserDefaults.standard.set(token, …)` | Plaintext plist, included in backups | Keychain (STK-SWIFT-07) |
| CocoaPods "because the README says pod install" | Second dependency system, workspace mutation | The SPM distribution (STK-SWIFT-04) |
| Icon-only buttons with no label | VoiceOver reads "button"; a11y audit fails | `.accessibilityLabel("…")` (STK-SWIFT-08) |
| `Task.detached` for ordinary async work | Escapes cancellation and actor context | `Task { }` / `async let` in scope (STK-SWIFT-03) |

## References

- Apple, "Migrating from the Observable Object protocol to the Observable macro" —
  the migration mechanics behind STK-SWIFT-02.
- Apple Swift Testing documentation — the `#expect`/`@Test` idiom in STK-SWIFT-06.
- Apple Keychain Services documentation — the storage mechanism behind STK-SWIFT-07.
- Apple Human Interface Guidelines, Accessibility — label phrasing guidance for
  STK-SWIFT-08.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
