---
name: govern
description: Use this skill at the START of any chunky development task, when creating or re-scoping a project, or when the user types /govern. Classifies the project's governance tier (T1-T4), detects stacks, selects the applicable standards from the governance framework, writes/updates GOVERNANCE.md, and emits a compact compliance brief. Also TRIGGER when a project's exposure changes (gets deployed, gains users, takes payment) — that's a re-classification event.
---

# govern — governance intake

Classify the task, select only the standards that apply, pin them in `GOVERNANCE.md`, and
brief the session. Governance repo: `~/Dev/claude-code/governance` (below: `$GOV`).

## Steps

### 1. Classify the tier

Read `$GOV/constitution/tiers.md` and apply the rubric **top-down, first match wins** to
what you know of the task/project. Sources: the user's brief, existing `GOVERNANCE.md`
(re-runs), the code itself (deploy configs, user-facing surfaces).

- Confident → proceed.
- Genuinely ambiguous between two tiers → ONE `AskUserQuestion`: both candidate tiers as
  options, each labeled with the rubric line that triggers it. Never silently guess.
- User overrides your classification → accept, record as `tier_override` in the manifest.

### 2. Detect stacks

From the repo (or the plan, for greenfield): `pyproject.toml`→python ·
`package.json`→typescript (+nextjs if next dep, +vite-react if vite+react) ·
`go.mod`→go · `Cargo.toml`→rust · `Package.swift`/`*.xcodeproj`→swiftui ·
`*.tf`→terraform,aws · `Dockerfile`→containers · lambda/serverless config→serverless,aws ·
sqlite/postgres/dynamo/redis usage in deps or config→that store · any browser-facing
surface→web. Allowed keys are the lint allowlist in `$GOV/templates/AUTHORING.md`.

### 3. Select standards (deterministic — do not browse standards/ by hand)

```bash
python3 $GOV/checks/select-standards.py --tier <T?> --stacks <k,k,k> \
  --brief-text "<the task description, verbatim>" --rules
```

The output is the selected set with parsed rules. Do NOT load `index.json` or unselected
standards into context. If `token_estimate` is huge (T3/T4 full product), that's expected —
you will load full docs only per-area while implementing; the brief below stays compact.

### 4. Write or update `GOVERNANCE.md`

Format: `$GOV/templates/GOVERNANCE-template.md`. New project → create from template.
Existing → update `tier`, `classified`, `stacks`, and `standards` pins (id+version from
the selection output). **Preserve** existing waivers, approvals, attestations,
`last_verified`. If pins changed versions, list the changes to the user (upgrades are
deliberate, never silent).

### 5. Emit the compliance brief

Compact, in your reply — not a file:

- Tier + one-line why (which rubric line fired).
- Selected standards: `ID vX.Y.Z — title` grouped required/advisory-triggered.
- **Hard rules for this task**: the rule IDs + one-line statements (from `--rules` output)
  that are `required` at this tier — this is what the session must honor.
- Reminder line: "Done = `/verify-compliance` green (Constitution C2)."

Constitution articles are assumed known (global CLAUDE.md loads them); don't restate.

## Rules

- Cheap by design: steps 1-3 are one script call + one file write. No deep repo reading.
- Never edit standards from here; a rule that seems wrong → note for `/harvest-learnings`.
- Escalation re-runs replace pins wholesale but keep waivers/attestations; downgrades
  (T3→T1) require the user to confirm.
