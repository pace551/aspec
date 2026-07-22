# Governance Manifest

```yaml
tier: T1
classified: 2026-07-22
tier_override: null
stacks: [nextjs, typescript, web]
standards:
  - {id: SEC-SECRETS, version: 1.0.1}
  - {id: STK-TS, version: 1.0.0}
  - {id: STK-NEXT, version: 1.0.0}
waivers: []
external_action_approvals: []
pii_inventory: n/a
last_verified: null
attestations:
  - {rule_id: STK-NEXT-01, followed: true, note: "App Router only; no pages/", date: 2026-07-22}
  - {rule_id: STK-NEXT-02, followed: true, note: "guest-form.tsx is the only client component", date: 2026-07-22}
  - {rule_id: STK-NEXT-03, followed: true, note: "signGuestbook parses via zod safeParse", date: 2026-07-22}
  - {rule_id: STK-NEXT-05, followed: true, note: "root template + per-page metadata", date: 2026-07-22}
  - {rule_id: STK-NEXT-09, followed: true, note: "output standalone; smoke serves it container-style", date: 2026-07-22}
```

## Notes

Worked example for STK-NEXT. T1 by rubric line 4: localhost only, single user. The
Playwright smoke (a T3+ gate) is included and green anyway because the example doubles
as the stack's living documentation.
