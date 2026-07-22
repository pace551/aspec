---
name: harvest-learnings
description: Use this skill at the end of a governed task (prompted by /implement-spec completion), when the user types /harvest-learnings, or whenever governance friction appeared mid-task — a rule that was missing, wrong, disproportionate, or whose verification tooling misfired. Runs a short governance-focused retro and captures candidate learnings as structured notes in the Obsidian vault Inbox for later promotion by /evolve-standards.
---

# harvest-learnings — governance retro capture

The framework evolves only through this pipeline: friction → vault note →
`/evolve-standards` promotion (Constitution C10). Never patch standards ad hoc from a
working session.

## Steps

### 1. Retro (against this session, honestly)

Answer from evidence in the session, not vibes:

- Which rule was **missing** — something went wrong or was decided ad hoc with no
  standard covering it?
- Which rule was **wrong** — followed it, and it produced a worse outcome here?
- Which rule was **friction** — correct in spirit, disproportionate at this tier
  (waivers granted this session are prime evidence)?
- Which **tooling** misfired — verification command flaky, false positive/negative,
  missing scanner?
- Did `/govern` select the right set — anything loaded-but-useless or needed-but-absent
  (trigger keyword gaps)?

Nothing real to report → say so and stop. Do not fabricate learnings (a session where
the framework just worked is the success case).

### 2. Write one note per distinct learning

Template: `~/Dev/claude-code/governance/templates/obsidian/governance-learning-template.md`.
Destination: `~/Documents/Obsidian/Personal/Inbox/YYYY-MM-DD governance <slug>.md`.
Frontmatter must carry `type: governance-learning`, `status: candidate`, the implicated
standard/rule IDs in `standards:` (or `[]` for missing-rule gaps), `project`, `tier`.
The **Proposed change** section is the payload — write it as the smallest diff
`/evolve-standards` could apply.

### 3. Show, then save

Present draft note(s) to the user for a quick yes/adjust (matching the house
obsidian-capture flow), then write the file(s) and confirm paths.

## Rules

- One note = one learning; don't bundle.
- Recurring waivers of the same rule across projects are always worth a note.
- Never edit the governance repo from this skill — capture only.
