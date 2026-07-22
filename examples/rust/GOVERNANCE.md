# Governance Manifest

```yaml
tier: T1
classified: 2026-07-22
tier_override: null
stacks: [rust]
standards:
  - {id: STK-RUST, version: 1.0.0}
  - {id: SEC-SECRETS, version: 1.0.1}
waivers: []
external_action_approvals: []
pii_inventory: n/a
last_verified: null
attestations: []
```

## Notes

Worked example for the governance framework (STK-RUST). T1 by rubric line 4: only James
runs it, local files only, no service, no external side effects. Bootstrapped from
`templates/scaffolds/rust/` on 2026-07-22. Not yet locally verified (no cargo on the
authoring machine) — run `scripts/lint.sh` and `scripts/test.sh` after installing the
Rust toolchain, then commit `Cargo.lock` and `.coverage-baseline`.
