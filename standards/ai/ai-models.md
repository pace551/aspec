---
id: AI-MODELS
title: Model Selection
family: AI
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - model selection
  - which model
  - claude
  - llm
  - model id
  - pricing
  - opus
  - sonnet
  - haiku
  - token cost
  - anthropic
requires: []
verification:
  - cmd: "attest: model names, pricing, and capabilities came from a live source (/claude-api skill or provider docs) at decision time, not memory"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-MODELS-01]
  - cmd: "attest: the model decision weighed task complexity, latency, cost per call × volume, and context needs"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-MODELS-02]
  - cmd: "attest: the chosen model and the reasons for it are recorded in the project CLAUDE.md or an ADR"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-MODELS-03]
  - cmd: "attest: production code paths pin exact model IDs — no latest/default aliases"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-MODELS-04]
    tiers: [T3, T4]
  - cmd: "attest: provider spend caps/alerts exist before volume traffic"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-MODELS-06]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Model Selection (AI-MODELS)

## Abstract

Retires two failure modes: choosing a model from stale memory (models churn monthly —
Constitution C8) and shipping an unpinned "latest" alias that silently changes behavior
and price under a running product. Compliance in one breath: model facts come from a live
source at decision time, the choice weighs complexity/latency/cost×volume/context, the
model and the *why* are recorded in `CLAUDE.md` or an ADR, production paths pin exact
model IDs, spend caps exist before volume, and the choice is re-examined on the monthly
fast-lane. Applies to any LLM provider, not just Anthropic.

## Normative Rules

### AI-MODELS-01 — Model facts MUST come from a live source at decision time, never memory

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Model names, pricing, context limits, and capabilities are consulted fresh — the
`/claude-api` skill for Anthropic, official docs for other providers — every time a
selection or cost estimate is made. Training memory is presumed stale (Constitution C8):
an agent that "remembers" a model tier or price is guessing, and guesses here compound
into wrong architectures and wrong budgets. This binds Claude Code itself during
implementation, not just human decisions.

### AI-MODELS-02 — Selection MUST weigh complexity, latency, cost × volume, and context needs

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The four decision inputs, considered explicitly: **task complexity** (does the task need
frontier reasoning, or is it classification/extraction a small model does at a fraction of
the price), **latency** (interactive UI vs batch pipeline), **cost per call × expected
volume** (a cheap-looking call at 100k invocations/month is the real number), **context
needs** (prompt + retrieved material + output vs the model's window). Default posture:
start with the smallest model that passes the eval set (`AI-ARCH-02`), escalate on
evidence, not vibes.

### AI-MODELS-03 — The chosen model and WHY MUST be recorded

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Project `CLAUDE.md` (or an ADR for weightier decisions) records: model ID, date chosen,
the four inputs from AI-MODELS-02 as one line each, and what would trigger
reconsideration. This is what makes the monthly re-evaluation (AI-MODELS-05) cheap — the
reasoning is on file, so "does a newer model beat it" is a comparison, not an
archaeology dig.

### AI-MODELS-04 — Production paths MUST pin exact model IDs — no "latest" aliases

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Code and config in anything deployed reference a dated, exact model ID, never a floating
alias: an alias that re-points is an unreviewed model migration in production — behavior,
cost, and token limits all change with no diff and no deploy. Upgrades happen as explicit
config changes that pass the eval set (`AI-ARCH-02`) first. Aliases are fine in scratch
scripts and exploration at T1/T2 — the line is production paths.

### AI-MODELS-05 — The model choice SHOULD be re-evaluated on the monthly fast-lane

**Tiers**: all advisory — **Layer**: A

`/evolve-standards`' monthly sweep includes a model-market pass: for each project with a
recorded model decision, check (live, per AI-MODELS-01) whether a newer/cheaper model
dominates on the recorded criteria. Outcome is one line in the decision record — "checked
2026-08, no change" is a perfectly good result. Re-evaluation without a recorded WHY is
impossible, which is the other half of AI-MODELS-03's value.

### AI-MODELS-06 — Provider spend caps MUST exist before volume traffic

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Paid LLM usage at scale is recurring spend under Constitution C6: before a deployed
product sends real traffic, the provider account has a hard spend cap or budget alert
sized to the cost model from AI-MODELS-02. `OPS-FINOPS` owns the alarm mechanics; this
rule makes the LLM provider one of the alarmed line items — API keys used by products are
the classic unmetered leak.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: model facts from live source at decision time | explicit yes | AI-MODELS-01 |
| 2 | attest: four decision inputs weighed | explicit yes | AI-MODELS-02 |
| 3 | attest: model + why recorded in CLAUDE.md/ADR | explicit yes | AI-MODELS-03 |
| 4 | attest: exact model IDs pinned in prod paths (T3+) | explicit yes | AI-MODELS-04 |
| 5 | attest: provider spend caps before volume (T3+) | explicit yes | AI-MODELS-06 |

**Remediation:** decision made from memory → redo the lookup via `/claude-api`, confirm or
amend the choice, then attest · alias found in prod config → replace with the exact ID it
currently resolves to (no behavior change), then upgrade deliberately · no decision record
→ reconstruct it now while reasons are fresh.

## Worked Example

Decision record in a project `CLAUDE.md` (values illustrative — always pull current ones
via `/claude-api` at decision time, per AI-MODELS-01):

```markdown
## Model decision (2026-07-22)
- Model: {exact dated model ID from /claude-api lookup}   # pinned in settings.yaml
- Complexity: extraction + classification — mid-tier model passes eval set 19/20
- Latency: batch overnight job — latency irrelevant
- Cost × volume: ~3k calls/mo × current per-call price — under budget alarm threshold
- Context: prompt+doc ≈ 8k tokens — any current window is fine
- Reconsider when: eval set grows past 20 cases, volume 10×, or monthly sweep finds
  a cheaper model passing the same evals
```

```yaml
# settings.yaml — the pin AI-MODELS-04 requires
llm:
  model: "{exact-model-id-2026xxxx}"   # never "-latest"
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Answering "which model should I use" from memory | Months-stale in a monthly-churn market | Live lookup, then decide (AI-MODELS-01) |
| `-latest` alias in a deployed path | Silent model migration: behavior/cost change with no diff | Pin exact ID; upgrade via eval-gated config change |
| Defaulting to the frontier model for everything | 10–50× cost for tasks a small model passes | Smallest model that passes the evals (AI-MODELS-02) |
| Cost estimated per call, not per call × volume | The bill scales with volume, the estimate didn't | Multiply by realistic monthly volume |
| Model choice in an old chat log, nowhere else | Unrecoverable reasoning; re-evaluation impossible | CLAUDE.md/ADR record (AI-MODELS-03) |
| Product API key with no spend cap | One retry loop away from a four-figure bill | Cap/alert before volume (AI-MODELS-06) |

## References

- `/claude-api` skill — the mandated live source for Anthropic model IDs, pricing, and
  limits (AI-MODELS-01).
- Constitution C8 — the invariant this standard operationalizes for model selection.
- Anthropic model deprecation/versioning docs — why dated IDs exist and aliases float
  (rationale for AI-MODELS-04).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
