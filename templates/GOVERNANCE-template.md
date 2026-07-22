# GOVERNANCE.md Template

Copy to `{project}/GOVERNANCE.md`. Written and updated by `/govern`; read by
`/verify-compliance`, the SessionStart banner hook, and humans. The YAML block is the
machine surface — keep it valid YAML; prose goes below it.

````markdown
# Governance Manifest

```yaml
tier: T1                        # T1 | T2 | T3 | T4
classified: 2026-07-22          # date of last /govern run
tier_override: null             # or {from: T2, to: T1, reason: "...", date: YYYY-MM-DD}
stacks: [python, sqlite]        # stack keys from index.json
standards:                      # pinned selected set — upgrades are deliberate
  - {id: SEC-SECRETS, version: 1.0.0}
  - {id: STK-PY, version: 1.0.0}
waivers: []                     # - {rule_id: SEC-SAST-02, reason: "...", expires: YYYY-MM-DD}
external_action_approvals: []   # - {action: "send email via SES", granted: YYYY-MM-DD}
pii_inventory: n/a              # T3+: list of {field, store, purpose, retention} or "none"
last_verified: null             # stamped by /verify-compliance on full pass
attestations: []                # advisory-rule self-reports, written by /verify-compliance
                                # - {rule_id: UX-FORMS-03, followed: true, note: "", date: YYYY-MM-DD}
```

## Notes

<!-- Free-form: why the tier is what it is, any context the YAML can't hold. -->
````

Rules:

- **Waiver expiry is mandatory** — `/verify-compliance` fails on any waiver past `expires`
  and nags within 14 days of it.
- **Version pins are the upgrade mechanism** — `/govern` diffs pinned versions against
  `index.json` and offers (never forces) upgrades, listing changed rules.
- Hand-edits are allowed (it's your project) but `/verify-compliance` re-validates the YAML
  schema on every run.
