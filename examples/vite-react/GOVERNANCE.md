# Governance Manifest

```yaml
tier: T1
classified: 2026-07-22
tier_override: null
stacks: [vite-react, typescript, web]
standards:
  - {id: SEC-SECRETS, version: 1.0.1}
  - {id: STK-TS, version: 1.0.0}
  - {id: STK-VITE, version: 1.0.0}
waivers: []
external_action_approvals: []
pii_inventory: n/a
last_verified: null
attestations:
  - {rule_id: STK-VITE-01, followed: true, note: "internal status dashboard; SEO irrelevant", date: 2026-07-22}
  - {rule_id: STK-VITE-02, followed: true, note: "all server state in useQuery/useMutation via src/api.ts", date: 2026-07-22}
  - {rule_id: STK-VITE-03, followed: true, note: "createBrowserRouter; route modules own structure", date: 2026-07-22}
  - {rule_id: STK-VITE-04, followed: true, note: "settings form uses zodResolver", date: 2026-07-22}
  - {rule_id: STK-VITE-05, followed: true, note: "errorElement on the root route; three states in home", date: 2026-07-22}
  - {rule_id: STK-VITE-06, followed: true, note: "React.lazy per route; verified per-route chunks in dist/", date: 2026-07-22}
```

## Notes

Worked example for STK-VITE. T1 by rubric line 4: localhost dashboard, single user.
The SPA choice is justified per STK-VITE-01: internal tool, known user, no SEO.
