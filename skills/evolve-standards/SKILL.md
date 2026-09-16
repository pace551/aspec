---
name: evolve-standards
description: Use this skill for the quarterly governance review, the monthly fast-lane review of fast-moving standards (AI models, dependency tooling), or when the user types /evolve-standards or asks to "review/update the governance framework" or "promote learnings". Clusters candidate learnings from the Obsidian vault into proposed standard diffs (human-approved), runs the staleness sweep, applies version bumps + changelogs, regenerates the index, and self-lints the framework.
---

# evolve-standards — the framework's only write path

Standards change here and nowhere else (Constitution C10). Every change: version bump +
changelog + regenerated index + clean self-lint. Governance repo:
`$GOV`.

## Mode selection

- **quarterly** (default): full pass — learnings, staleness, self-lint.
- **fast-lane** (monthly, or on request): only `AI-MODELS` + `DEV-DEPS` + anything whose
  `triggers` include fast-churn tooling; consult live sources (`/claude-api` skill for
  model facts, registries/official docs for tools — never memory, Constitution C8).
- **ad-hoc**: user brought a specific change → still follows steps 2-5.

## Steps

### 1. Gather candidates

```bash
rg -l "type: governance-learning" $VAULT/ | \
  xargs rg -l "status: candidate"
```

Read each note; cluster by implicated standard/rule ID. Also mine recurring-waiver
signals: the same rule waived in two projects is a candidate without a note.

### 2. Propose diffs (STOP gate — nothing applies without approval)

Per cluster, draft the smallest change: rule text edit, tier-tag change, new rule
(next contiguous number, never renumber), trigger keyword, verification fix, or a new
standard (rare — needs the template + AUTHORING pass). Version bump semantics: patch =
wording/verification fix, minor = new rule or tier change, major = breaking rework.
Present all proposed diffs with rationale + source notes. **STOP for approval**; the user
picks per-diff.

### 3. Apply approved diffs

Edit the standard(s): content + `version` + `## Changelog` entry + `last_review: today`.
Framework-shape changes (schema, tiers, families) additionally need an ADR in
`$GOV/decisions/` (use the template).

### 4. Staleness sweep

List standards with `last_review` older than 90 days (quarterly) / fast-lane set older
than 30 days (read from `$GOV/index.json` with a python/jq one-liner). For each: skim
for rot (dead links, tool/version churn); fine → bump `last_review` only (this
metadata-only touch is the one edit exempt from a version bump — note it in the retro,
not the changelog); rotten → fold into step 2's proposals.

### 5. Regenerate, lint, close the loop

```bash
python3 $GOV/checks/build-index.py && python3 $GOV/checks/lint-framework.py
```

Both must be clean. Mark promoted vault notes `status: promoted` (rejected →
`status: rejected` + one-line reason in the note). Write the sweep retro note to the
vault Inbox from `$GOV/templates/obsidian/governance-retro-template.md`. Commit the
governance repo (conventional message listing standard version changes); remind that
projects whose pins now trail upgrade deliberately via `/govern` on next touch.

## Rules

- No approval, no edit — this skill never self-applies substantive changes.
- Rule IDs are permanent; retirement syntax per the standard template.
- If a proposed change contradicts the Constitution, the answer is an ADR + user
  decision, not a quiet standard edit.
