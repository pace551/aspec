# Governance Manifest

```yaml
tier: T1
classified: 2026-07-22
tier_override: null
stacks: [swiftui]
standards:
  - {id: SEC-SECRETS, version: 1.0.1}
  - {id: STK-SWIFT, version: 1.0.0}
waivers: []
external_action_approvals: []
pii_inventory: n/a
last_verified: null
attestations:
  - {rule_id: STK-SWIFT-01, followed: true, note: "library only; no UI code, no UIKit", date: 2026-07-22}
  - {rule_id: STK-SWIFT-03, followed: true, note: "no async surface yet; nothing callback-based", date: 2026-07-22}
  - {rule_id: STK-SWIFT-05, followed: true, note: "logic in CounterModel, deps via init, tested without UI", date: 2026-07-22}
  - {rule_id: STK-SWIFT-08, followed: true, note: "no interactive elements in a library target", date: 2026-07-22}
```

## Notes

Worked example for STK-SWIFT. T1 by rubric line 4: a local library only James builds.
Deliberate trim per STK-SWIFT-06: no hosted CI — verification is
`checks/stk-swift-verify.sh` (`swift test`). On this machine (Command Line Tools only,
no Xcode) the toolchain ships no XCTest/Testing modules: `swift build` is green, and
the verify script degrades with its documented warning — STK-SWIFT-06 is satisfied by
this note, not by a green suite, until run on a machine with Xcode.
