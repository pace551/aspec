# Governance Manifest

```yaml
tier: T1
classified: 2026-07-22
tier_override: null
stacks: [htmx, python, web]
standards:
  - {id: SEC-SECRETS, version: 1.0.1}
  - {id: STK-PY, version: 1.0.1}
  - {id: STK-HTMX, version: 1.0.0}
waivers: []
external_action_approvals: []
pii_inventory: n/a
last_verified: null
attestations:
  - {rule_id: STK-HTMX-01, followed: true, note: "CRUD todo app; server owns all state", date: 2026-07-22}
  - {rule_id: STK-HTMX-03, followed: true, note: "all posts work without JS (303 redirect)", date: 2026-07-22}
  - {rule_id: STK-HTMX-04, followed: true, note: "double-submit cookie dependency on all POSTs", date: 2026-07-22}
  - {rule_id: STK-HTMX-05, followed: true, note: "hx-indicator + hx-disabled-elt on both forms", date: 2026-07-22}
  - {rule_id: STK-HTMX-06, followed: true, note: "no JSON routes exist", date: 2026-07-22}
```

## Notes

Worked example for STK-HTMX. T1 by rubric line 4: localhost only, single user, no
deployment. The hypermedia routes are the entire API surface (STK-HTMX-06); tests
assert both full-page and fragment modes per STK-HTMX-02/-07.
