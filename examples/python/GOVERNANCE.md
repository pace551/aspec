# Governance Manifest

```yaml
tier: T1
classified: 2026-07-22
tier_override: null
stacks: [python, sqlite]
standards:
  - {id: STK-PY, version: 1.0.1}
  - {id: SEC-SECRETS, version: 1.0.1}
waivers: []
external_action_approvals: []
pii_inventory: n/a
last_verified: null
attestations: []
```

## Notes

Worked example for the governance framework (STK-PY + SQLite pattern). T1 by rubric
line 4: only James runs it, local files only, no service, no external side effects.
Bootstrapped from `templates/scaffolds/python/` on 2026-07-22.
