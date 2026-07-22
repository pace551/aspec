# Obsidian Governance-Learning Template

Written by `/harvest-learnings` to `~/Documents/Obsidian/Personal/Inbox/` as
`YYYY-MM-DD governance <slug>.md`. Matches the vault's existing frontmatter conventions
(`obsidian-capture` skill) with governance-specific extensions that `/evolve-standards`
greps for.

````markdown
---
date: YYYY-MM-DD
type: governance-learning
areas:
  - ai-learning
tags:
  - governance
  - <topic-tag>
source: claude
status: candidate            # candidate → promoted | rejected  (set by /evolve-standards)
standards:                   # implicated standard/rule IDs; [] if the gap is "no standard exists"
  - SEC-SECRETS-03
project: <project-name>
tier: T2
---

# <What we learned, one sentence, sentence case>

## What happened
2-4 sentences: the concrete situation. Task, tier, what the framework said, what reality said.

## The gap
One of: **missing rule** (nothing covered this) · **wrong rule** (rule said X, X was wrong
here) · **friction** (rule correct but disproportionate at this tier) · **tooling** (rule
fine, verification command broken/noisy).

## Proposed change
The smallest edit that would have prevented this: new rule text, tier-tag change, trigger
keyword to add, verification command fix. Written so /evolve-standards can turn it into a
diff. If unsure, say what evidence would decide it.

## Evidence
Links/paths: the session, the diff, the failing command output.
````
