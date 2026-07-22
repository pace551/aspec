---
id: ARC-CONFIG
title: Configuration
family: ARC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - config
  - configuration
  - settings.yaml
  - environment variable
  - env var
  - dotenv
  - feature flag
  - pydantic settings
  - 12-factor
  - startup validation
requires: [SEC-SECRETS]
verification:
  - cmd: "sh -c '[ ! -f settings.yaml ] || git ls-files --error-unmatch settings.yaml >/dev/null 2>&1'"
    expect: "exit 0 — settings.yaml, when present, is committed (it is non-secret by definition)"
    layer: G
    rules: [ARC-CONFIG-01]
    tiers: [T2, T3, T4]
  - cmd: "attest: settings.yaml holds only non-secret values; everything secret arrives via the environment per SEC-SECRETS"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONFIG-01]
  - cmd: "attest: config loads into one typed, validated object and the process refuses to boot on invalid config"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONFIG-02]
  - cmd: "attest: environment lookups live only in the config module; no scattered os.environ/process.env"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONFIG-03]
  - cmd: "attest: feature flags are fields on the config object and documented in the README"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONFIG-04]
last_review: 2026-07-22
---

# Configuration (ARC-CONFIG)

## Abstract

12-factor config, house-flavored. Two files per project: `settings.yaml` — non-secret,
committed, human-edited — and `.env` — secret, gitignored, governed by `SEC-SECRETS`.
Both load through one config module into a typed object (pydantic `Settings` / zod)
validated at import: invalid or missing config kills the process at boot with the
offending field named, never at 2 a.m. mid-run. No `os.environ` scattered through code,
no `if env == "prod"` forks; feature flags are config fields, documented in the README.
Advisory at T1, required from T2 up — reproducible research needs reproducible config.

## Normative Rules

### ARC-CONFIG-01 — Config MUST come from the environment plus committed `settings.yaml`; secrets only via the environment

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G + A

The split is by secrecy, not by format: `settings.yaml` carries every non-secret knob
(intervals, model names, thresholds, flags) and is committed — it is documentation that
executes. Secrets arrive only through the environment, locally via gitignored `.env`
(`SEC-SECRETS-02`; the secret-scan gate keeps `settings.yaml` honest). No third channel:
config JSON blobs in the database, hardcoded constants marked "tune later", or CLI flags
duplicating settings all fragment the picture of what the process will do.

### ARC-CONFIG-02 — Config MUST load into one typed object validated at startup; the process refuses to boot on invalid config

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

One `Settings` class (pydantic-settings in Python, a zod schema in TS) declares every
field with type and default; construction happens once at startup and a validation error
is fatal — the message names the missing/invalid field. This converts every
config-shaped bug from a mid-run `KeyError` into a boot-time failure, which for launchd
jobs is the difference between a red log line at load and a half-completed run
(`ARC-ERRORS-03` is the general principle; this is its config instance).

### ARC-CONFIG-03 — Config access MUST go through the one config module

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

`os.environ` / `os.getenv` / `process.env` appear in exactly one file — the config
module; everything else imports the settings object. Scattered lookups defeat startup
validation (rule 02) one call site at a time and make "what does this deploy actually
read?" unanswerable. The same discipline bans scattered `if ENV == "prod":` forks —
environment differences are expressed as named config values, so behavior is testable by
constructing a `Settings`, not by monkeypatching the world.

### ARC-CONFIG-04 — Feature flags are config: typed fields, documented in the README, short-lived

**Tiers**: all advisory — **Layer**: A (attestation)

A flag is a boolean (or small enum) field on the config object, default matching current
production behavior, with a README line saying what it gates and when it can be deleted.
No flag services, no commented-out code as a flag, no env var checked inline
(rule 03). Flags exist to enable `ARC-PATTERNS-04` (ship dark, merge early); a flag that
survives past full rollout is debt — delete it and its dead branch.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `[ ! -f settings.yaml ] \|\| git ls-files --error-unmatch settings.yaml` (T2+) | exit 0 — settings.yaml committed if present | ARC-CONFIG-01 |
| 2 | attestation (secrecy split) | explicit yes recorded | ARC-CONFIG-01 |
| 3–5 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-CONFIG-02…04 |

**Remediation:** `settings.yaml` untracked → it either contains a secret (move it to
`.env`, then commit the rest) or was simply never added (`git add settings.yaml`) ·
scattered `os.getenv` → move each into a `Settings` field, import the object at the call
sites · config validated lazily → construct `Settings` at module import / app factory,
not inside handlers.

## Worked Example

The house pattern for a Python project (`STK-PY` layout):

```yaml
# settings.yaml — non-secret, committed (ARC-CONFIG-01)
poll_interval_minutes: 30
summary_model: claude-sonnet-4-5
enable_email_digest: false   # flag (ARC-CONFIG-04): delete after digest GA
```

```python
# src/myproj/config.py — the single config module (ARC-CONFIG-03)
from pathlib import Path
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")  # secrets via env (SEC-SECRETS)
    anthropic_api_key: str                              # no default: boot fails if absent
    poll_interval_minutes: int = 30
    summary_model: str = "claude-sonnet-4-5"
    enable_email_digest: bool = False

def _load() -> Settings:
    file_cfg = yaml.safe_load(Path("settings.yaml").read_text()) or {}
    return Settings(**file_cfg)   # ValidationError here = refuse to boot (ARC-CONFIG-02)

settings = _load()
```

Every other module writes `from myproj.config import settings` — nothing else touches
`os.environ`.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `os.getenv("X")` at 14 call sites | Startup validation defeated; failures surface mid-run, one site at a time | One config module (ARC-CONFIG-03) |
| `os.getenv("KEY", "sk-…")` fallback | Hardcoded secret with extra steps — `SEC-SECRETS-02` violation | No secret defaults; fail at boot |
| `if os.environ.get("ENV") == "prod":` scattered | Untestable forks; staging silently diverges | Named config values (ARC-CONFIG-03) |
| Lazy config read deep in the call stack | The 2 a.m. launchd run dies halfway instead of at load | Validate at startup (ARC-CONFIG-02) |
| Secrets in `settings.yaml` "just for now" | It's committed — that's a leak (`SEC-SECRETS-01`) | Secrecy split (ARC-CONFIG-01) |
| Commented-out code as a feature toggle | Invisible state; diverges instantly | Typed flag field (ARC-CONFIG-04) |
| Config values duplicated as CLI flags "for convenience" | Two sources of truth disagree eventually | Flags override nothing; one source |

## References

- The Twelve-Factor App, factor III "Config" — the env-var discipline; this standard adds
  the committed-non-secret file the pure form lacks.
- pydantic-settings documentation — the `BaseSettings` + `env_file` mechanics in the
  worked example.
- `SEC-SECRETS` pilot standard — owns the secret half of the split; ARC-CONFIG-01 is its
  non-secret complement.
- zod documentation (`z.object().parse(process.env)`) — the TypeScript equivalent of
  boot-time validation.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
