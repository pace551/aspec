---
name: verify-compliance
description: The "done" gate. Use this skill BEFORE declaring any governed task complete, when the user types /verify-compliance, when /implement-spec reaches its final gate, or when the user asks "is this compliant / ready". Runs every applicable standard's verification commands against the project, reports a deterministic pass/fail table, collects attestations for advisory rules, and refuses "done" while required checks fail.
---

# verify-compliance — the done gate

Work is not done until this passes (Constitution C2). Deterministic scripts verify; you
comply and remediate. Governance repo: `~/Dev/claude-code/governance` (below: `$GOV`).

## Steps

### 1. Run the executor

```bash
python3 $GOV/checks/run-verification.py --project <repo-root>
```

It reads `GOVERNANCE.md` (no manifest → tell the user to run `/govern` first, stop),
filters checks by tier, skips waived rules, fails expired waivers, and executes every H/G
command from the project root.

### 2. Report honestly

Show the user the result table as-is: PASS/FAIL/WAIVED per check, failure output
included. Never soften a FAIL, never summarize failures away. If a check errored for
environmental reasons (tool missing), say exactly that — it is still not a PASS.

### 3. Remediate failures

For each FAIL: consult the owning standard's **Verification → Remediation** section
(path from `$GOV/index.json` via the standard id) and fix the underlying issue — never
the check. Weakening a gate (lowering baseline, adding lint ignores, deleting a check)
requires the user to grant a waiver per `$GOV/templates/waiver-template.md` (waivers are
human-granted; you may draft one and STOP for approval). Re-run step 1 until green.

### 4. Attestations (advisory layer — forced, not optional)

The run emits `attestations_pending`. For each item, answer honestly from what you
actually did this session: `followed: true` only if you can point at evidence;
`followed: false` + one-line note otherwise (that is allowed — drift must be visible,
Constitution C9). Write them into `GOVERNANCE.md`'s `attestations:` list
(`{rule_id, followed, note, date}` — replace stale entries for the same rule_id).

### 5. Stamp and summarize

On full pass: `python3 $GOV/checks/run-verification.py --project <root> --stamp` (writes
`last_verified`). Final summary states: checks passed/waived counts, attestations
recorded (any `followed: false` called out), and any WARN about version pins drifting
from the repo (suggest re-running `/govern` to upgrade deliberately).

## Rules

- Non-negotiable: exit-nonzero from the executor means the task is NOT done. Report it
  as not done. There is no "mostly passing".
- Never mark an attestation true to make the summary tidy.
- A check that keeps being waived/failed across sessions is a signal — suggest
  `/harvest-learnings`.
