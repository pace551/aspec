# Authoring Brief — writing standards for this framework

Read this first, then in order: `constitution/CONSTITUTION.md`, `constitution/tiers.md`,
`constitution/glossary.md`, `templates/standard-template.md`, and both pilot standards
(`standards/security/sec-secrets.md`, `standards/stacks/stk-py.md`). The pilots are the
calibration bar for depth, tone, and length — match them.

## Hard requirements

1. **File placement**: `standards/{family-dir}/{id-lowercase}.md`. Family dirs:
   SEC→`security` TST→`testing` ARC→`architecture` STK→`stacks` INF→`infra`
   OPS→`operations` DEV→`process` UX→`ux` DATA→`data` AI→`ai` LEG→`legal`.
2. **Self-check before finishing**:
   `python3 checks/lint-framework.py standards/<dir>/<file>.md` clean for every file you
   wrote. Do **not** run `build-index.py` (shared state; the merge step runs it).
3. **Verification commands must be real.** Every `cmd` either (a) runs as-is from a
   project root, (b) invokes a script you also write under `checks/` (executable,
   `set -euo pipefail` for bash, argument `--project DIR` optional), or (c) is an
   attestation entry starting `attest: …` with `layer: A`. Never invent a tool; if a
   needed scanner may be missing locally, follow the `checks/secret-scan.sh` pattern:
   use it if installed, degrade to a documented fallback, never silently pass.
4. **Tier honesty**: think through all four tiers per rule. T1 is advisory for almost
   everything outside SEC-SECRETS/git hygiene. Use the exact tier-line format from the
   pilots (`**Tiers**: … — **Layer**: …`); a rule with `required` anywhere needs H/G
   verification coverage or the literal marker `**Layer**: A (attestation)`.
5. **Length**: ≤350 lines per doc; Abstract ≤120 words; T4-only docs proportionate
   (~120-180 lines), never padded.
6. **Cross-reference by ID** (`SEC-SECRETS`, `OPS-OBS`) — never by path. Reference
   standards from other families freely even if not yet written (the full-corpus lint at
   merge resolves them); keep `requires:` minimal per template rule 7.
7. **Triggers** are lowercase task-brief keywords a `/govern` intake would grep for —
   think "what words appear in a task that makes this standard relevant" (tools, nouns,
   verbs), not taxonomy labels.
8. **Stack keys vocabulary** (for `stacks:` frontmatter): `python`, `typescript`, `go`,
   `rust`, `nextjs`, `vite-react`, `htmx`, `swiftui`, `sqlite`, `postgresql`, `dynamodb`,
   `redis`, `terraform`, `containers`, `serverless`, `aws`, `web` (any browser-facing
   stack). Cross-cutting standards usually say `all`.
9. **Version `1.0.0`, status `active`, `last_review: 2026-07-22`**, changelog entry
   `- **1.0.0** (2026-07-22) — Initial version.`
10. **House context to honor**: solo developer (James), macOS, AWS as the cloud, GitHub +
    Actions, Claude Code as the implementing agent, free/open tooling by default
    (Constitution C6). Personal-scale pragmatism beats enterprise ceremony — every rule
    must earn its weight at the tier where it's required.

## Voice

RFC-2119 verbs in rule statements; precise, compact prose; no filler ("it is important
to…"), no restating the obvious; anti-pattern tables carry the scar tissue; references
explain *why* each source is cited. Write rules an agent can act on without asking a
human what was meant.
