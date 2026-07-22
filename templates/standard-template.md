# Standard Template

Copy this file to `standards/{family-dir}/{id-lowercase}.md` and fill every section. The
frontmatter is the API: `checks/build-index.py` parses it into `index.json` and
`checks/lint-framework.py` enforces the schema. Humans read the Abstract; agents act on the
Normative Rules; `/verify-compliance` executes the `verification` block.

Delete all guidance comments (`<!-- ... -->`) in the real file.

````markdown
---
id: FAM-SHORTNAME              # stable forever; FAMILY code + short name, uppercase
title: Human Readable Title
family: FAM                    # SEC|TST|ARC|STK|INF|OPS|DEV|UX|DATA|AI|LEG
version: 1.0.0                 # per-file semver; bump on ANY content change
status: active                 # draft | active | deprecated
tiers:                         # applicability per tier: required | advisory | n/a
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all                    # `all`, or a list of stack keys, e.g. [python, nextjs]
triggers:                      # lowercase keywords /govern matches against the task brief
  - example keyword
  - another phrase
requires: []                   # standard IDs co-loaded with this one (kept minimal)
verification:                  # executed by /verify-compliance, in order
  - cmd: "exact command, run from project root"
    expect: "exit 0"           # or a short description of the passing condition
    layer: G                   # H | G | A  (A = the attestation checklist item)
    rules: [FAM-SHORTNAME-01]  # rule IDs this command evidences
last_review: 2026-07-22        # bumped by /evolve-standards sweeps even without changes
---

# {title} ({id})

## Abstract

<!-- ≤120 words, for a human deciding whether this applies. What risk does this standard
     retire, what does compliance look like in one breath, what varies by tier. -->

## Normative Rules

<!-- Each rule: stable ID, one-line bold statement with RFC-2119 verb, tier tags,
     enforcement layer, then 1-4 sentences of precision (scope, exceptions, definitions).
     Rule IDs are never renumbered; retired rules stay listed with ~~strikethrough~~ and
     status note. Order rules by importance, not chronology. -->

### FAM-SHORTNAME-01 — {Bold one-line statement with MUST/SHOULD/MAY}

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

{Precision paragraph: exactly what satisfies the rule, what is out of scope, edge cases.}

### FAM-SHORTNAME-02 — …

## Verification

<!-- Human-readable expansion of the frontmatter verification block: the exact commands,
     what output means pass vs fail, and remediation hints for common failures.
     Every command here MUST appear in frontmatter and vice versa. -->

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `…` | exit 0 | FAM-SHORTNAME-01 |

**Remediation:** {common failure → fix, one line each}

## Worked Example

<!-- Smallest realistic demonstration of full compliance: config snippet, code fragment, or
     pointer into examples/. Runnable or copy-pasteable, not pseudocode. -->

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| … | … | … |

## References

<!-- External sources (specs, OWASP pages, vendor docs) with WHY each is cited. -->

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
````

## Authoring rules (enforced by `lint-framework.py`)

1. **Frontmatter completeness** — every key above present; `tiers` has all four tiers;
   `verification` non-empty unless the standard is 100% advisory (then it MUST contain at
   least one `layer: A` attestation entry).
2. **Rule backing** — every rule tagged `required` at any tier appears in some
   `verification.rules` list with layer H or G, OR carries the explicit marker
   `**Layer**: A (attestation)` in its body.
3. **ID discipline** — filename = lowercase `id` (`SEC-SECRETS` → `sec-secrets.md`);
   rule IDs are `{id}-NN`, contiguous from 01, never reused.
4. **Version discipline** — any content change bumps `version` and adds a Changelog line.
   `build-index.py` hashes bodies and refuses to index an edited-but-unbumped file.
5. **Length discipline** — Abstract ≤120 words. Whole doc SHOULD be ≤350 lines; the token
   budget for a typical selected set is ~15k, and every line here spends it.
6. **Tier honesty** — if a rule is meaningfully different per tier, split the difference
   into the tier tags, don't average it. "T1: advisory" is a real answer.
7. **requires minimalism** — `requires` is for standards whose rules are unintelligible
   without the other doc, not for thematic neighbors. Two hops max will be loaded.
