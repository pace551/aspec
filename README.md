# governance

Personal development governance framework: the constitution, standards corpus, scaffolds,
CI templates, skills, and enforcement machinery that make Claude Code deliverables secure,
tested, observable, and maintainable **by rule rather than by mood** — scaled across four
tiers from personal scripts (T1) to commercial products (T4).

**New here? Read [`docs/GUIDE.md`](docs/GUIDE.md)** — the developer walkthrough (mental
model, skill lifecycle, GOVERNANCE.md anatomy, waivers, evolution loop, troubleshooting).
This README is the summary.

## How it works

1. **`constitution/CONSTITUTION.md`** — ten invariants, always loaded, every task.
2. **`standards/`** — 67 standards in 11 families. Each has RFC-2119 rules with stable IDs,
   per-tier applicability, machine-run verification commands, a worked example, and
   anti-patterns. Frontmatter is the API.
3. **`index.json`** — generated catalog. `/govern` classifies a task's tier, detects
   stacks, filters the index on tier/stacks/triggers, and loads *only* the matching
   standards (budget: ≤~15k tokens for a typical selected set).
4. **`GOVERNANCE.md`** (per project) — tier, pinned standard versions, waivers,
   attestations. `/verify-compliance` executes every listed standard's verification
   commands; **work is not "done" until it passes.**
5. **Enforcement is layered** — H (hooks that block actions), G (CI / verify gates that
   block "done"), A (advisory with forced attestation). Nothing is advisory-and-invisible.
6. **Evolution** — learnings are harvested to the Obsidian vault Inbox; `/evolve-standards`
   promotes durable ones as versioned diffs. `checks/build-index.py` refuses to index a
   changed-but-unbumped standard.

## Daily use

| Moment | Do |
|---|---|
| Starting a chunky task | `/govern` → tier + compliance brief |
| New project | `/bootstrap-repo` → scaffold + CI + hooks + GOVERNANCE.md |
| Before calling anything done | `/verify-compliance` |
| Something felt wrong/missing | `/harvest-learnings` |
| Quarterly (or model churn) | `/evolve-standards` |

## Maintenance

```bash
python3 checks/build-index.py     # regenerate index.json + INDEX.md
python3 checks/lint-framework.py  # full self-lint (schema, rules, freshness)
checks/install.sh                 # install skills (+ optionally hooks) globally
```

Framework-shape changes (new family, frontmatter schema, tier model) require an ADR in
`decisions/`. Standard content changes require a version bump + changelog line.
