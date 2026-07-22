---
id: STK-RUST
title: Rust Stack
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [rust]
triggers:
  - rust
  - cargo
  - clippy
  - rustfmt
  - crate
  - unwrap
  - thiserror
  - anyhow
requires: [SEC-SECRETS]
verification:
  - cmd: "cargo fmt --check"
    expect: "exit 0 — no file needs reformatting"
    layer: G
    rules: [STK-RUST-01]
  - cmd: "cargo clippy --all-targets -- -D warnings"
    expect: "exit 0 — warnings are errors; unwrap_used/expect_used denied via [lints] (STK-RUST-03)"
    layer: G
    rules: [STK-RUST-02, STK-RUST-03]
  - cmd: "cargo test"
    expect: "exit 0 — a crate with no tests yet passes trivially (fresh scaffold tolerated; TST-POLICY governs test existence)"
    layer: G
    rules: [STK-RUST-04]
  - cmd: "sh -c 'command -v cargo-llvm-cov >/dev/null 2>&1 || { echo \"cargo-llvm-cov not installed: cargo install cargo-llvm-cov\" >&2; exit 1; }; cargo llvm-cov --lcov --output-path lcov.info >/dev/null 2>&1; python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py --check'"
    expect: "coverage ≥ committed .coverage-baseline (read-only check; lcov.info is gitignored output; fails loudly if cargo-llvm-cov missing)"
    layer: G
    rules: [STK-RUST-04]
    tiers: [T2, T3, T4]
  - cmd: "sh -c 'command -v cargo-audit >/dev/null 2>&1 || { echo \"cargo-audit not installed: cargo install cargo-audit\" >&2; exit 1; }; cargo audit'"
    expect: "exit 0 (per-advisory waivers handled by /verify-compliance; fails loudly if cargo-audit missing)"
    layer: G
    rules: [STK-RUST-05]
    tiers: [T2, T3, T4]
  - cmd: "sh -c 'test -f Cargo.lock && ! git check-ignore -q Cargo.lock'"
    expect: "exit 0 — lockfile exists and is not gitignored"
    layer: G
    rules: [STK-RUST-06]
  - cmd: "attest: every remaining unwrap()/expect() is in test code or sits on a provable invariant with a // INVARIANT: comment"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-RUST-03]
  - cmd: "attest: crate layout matches project size (single crate, or workspace with crates/ once a second crate exists)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-RUST-07]
  - cmd: "attest: canonical-library table consulted for any new dependency"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-RUST-08]
last_review: 2026-07-22
---

# Rust Stack (STK-RUST)

## Abstract

House rules for every Rust project: `cargo fmt --check` and `clippy -D warnings` are the
gates, error handling splits by crate kind (libraries define typed errors with
`thiserror`, binaries propagate with `anyhow`), `unwrap()`/`expect()` are denied outside
tests and documented invariants via Cargo `[lints]`, `cargo test` with cargo-llvm-cov
feeding the coverage ratchet, cargo-audit as SCA, `Cargo.lock` always committed.
Identical toolchain at every tier — tier scales test depth and CI, not tool choice.
Scaffold: `templates/scaffolds/rust/` · CI: `templates/ci/rust.yml` · worked example:
`examples/rust/`.

## Normative Rules

### STK-RUST-01 — Code MUST be `cargo fmt --check` clean; formatting is not a discussion

**Tiers**: all required — **Layer**: G

Default rustfmt, no `rustfmt.toml` unless a specific rule earns its keep (record why in
the project `CLAUDE.md`). Generated code is excluded via `#[rustfmt::skip]` on the item,
not by weakening global config.

### STK-RUST-02 — `cargo clippy --all-targets -- -D warnings` MUST pass

**Tiers**: all required — **Layer**: G

Warnings are errors — in clippy and in rustc. `--all-targets` covers tests, benches, and
examples so test code meets the same bar. Suppressions are the narrowest possible
`#[allow(clippy::rule)]` on the item with a trailing `// reason` comment; crate-level
`#![allow]` is reserved for the test-code carve-outs in STK-RUST-03. Never
`-A warnings` or deleting lints from `[lints]` to make a gate green.

### STK-RUST-03 — Error handling MUST split thiserror/anyhow by crate kind; no unwrap()/expect() outside tests and documented invariants

**Tiers**: all required — **Layer**: G

Libraries (anything with callers) define typed error enums with `thiserror` so callers
can match; binaries' `main`/wiring use `anyhow::Result` with `.context(…)` for
human-readable chains. The boundary: typed until the point where nobody branches on the
error anymore. `unwrap()`/`expect()` are denied mechanically — the scaffold's Cargo
`[lints.rust]`/`[lints.clippy]` set `unwrap_used`/`expect_used` to `deny` — and allowed
only (a) in test code under `#![allow(clippy::unwrap_used, clippy::expect_used)]`, or
(b) on a provable invariant with an adjacent `// INVARIANT:` comment plus a scoped
`#[allow]`. `panic!` is for unreachable programmer errors only.

### STK-RUST-04 — `cargo test` MUST be green and coverage MUST never drop below the committed baseline

**Tiers**: all required — **Layer**: G

Unit tests live in `#[cfg(test)] mod tests` beside the code; integration tests in
`tests/`. "cargo test green" is required at every tier; at T2+ coverage comes from
`cargo llvm-cov --lcov --output-path lcov.info` (the LCOV format
`checks/coverage-ratchet.py` reads) and the committed `.coverage-baseline` only moves up.
cargo-llvm-cov is a one-time `cargo install`; its absence fails the gate loudly rather
than skipping it.

### STK-RUST-05 — cargo-audit MUST be clean, or findings waived per-advisory

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`cargo audit` checks `Cargo.lock` against the RustSec advisory database. Fix by upgrade
first; waive per-advisory in `GOVERNANCE.md`
(`{rule_id: STK-RUST-05, reason: "RUSTSEC-… not reachable because …", expires}`) — never
a standing ignore list in `audit.toml`. Unmaintained-crate warnings are prompts to find a
maintained replacement, not noise (cadence in `DEV-DEPS`).

### STK-RUST-06 — `Cargo.lock` MUST be committed, for libraries as well as binaries

**Tiers**: all required — **Layer**: G

Committed always — it is what makes builds, CI, and `cargo audit` reproducible, and
current cargo guidance has dropped the old "libraries shouldn't commit it" advice.
Library compatibility with downstream resolution is covered by honest semver bounds in
`Cargo.toml`, not by leaving the lockfile untracked. `cargo update` is a deliberate,
reviewed commit.

### STK-RUST-07 — Layout SHOULD be a single crate until a second crate is real, then a workspace under `crates/`

**Tiers**: all advisory — **Layer**: A (attestation)

Start with one crate: `src/lib.rs` holding the logic, `src/main.rs` as a thin binary over
the lib (this is what makes the binary testable). Split into a `[workspace]` with
`crates/{name}/` members only when a second binary or genuinely shared library exists —
speculative workspace scaffolding is enterprise ceremony at solo scale. Workspace
members share one `Cargo.lock` and inherit `[workspace.lints]`/`[workspace.dependencies]`
so versions and lint policy stay single-sourced.

### STK-RUST-08 — New dependencies SHOULD come from the canonical-libraries table

**Tiers**: all advisory — **Layer**: A (attestation)

| Need | Use | Not | Why |
|---|---|---|---|
| Library errors | `thiserror` | hand-rolled `impl Error`, `Box<dyn Error>` in APIs | typed, matchable (STK-RUST-03) |
| Binary errors | `anyhow` + `.context()` | `unwrap()` chains | readable failure chains (STK-RUST-03) |
| Serialization | `serde` (+ `serde_json`) | hand-rolled parsing | the ecosystem standard |
| CLI | `clap` (derive) | raw `std::env::args` beyond trivial | typed args, generated help; commander/argparse analog |
| HTTP client | `reqwest` | hand-rolled hyper | boring default, rustls-capable |
| Async runtime | `tokio` — only when async is needed | async-by-reflex, mixing runtimes | sync Rust is simpler and usually enough |
| Logging | `tracing` | `println!` in services, `log` for new code | structured spans, `OPS-OBS` house logger |
| Dates | `chrono` | `std::time` arithmetic for calendars | timezone-aware, ubiquitous |

Deviating is fine with a reason (that's SHOULD) — the choice is made once, here, not
re-litigated per session.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `cargo fmt --check` | exit 0 | STK-RUST-01 |
| 2 | `cargo clippy --all-targets -- -D warnings` | exit 0 | STK-RUST-02, -03 |
| 3 | `cargo test` | exit 0 | STK-RUST-04 |
| 4 | cargo-llvm-cov → `coverage-ratchet.py --check` (T2+) | ≥ `.coverage-baseline`; loud fail if tool missing | STK-RUST-04 |
| 5 | `cargo audit` (T2+) | exit 0 / per-advisory waivers; loud fail if tool missing | STK-RUST-05 |
| 6 | `Cargo.lock` exists and not gitignored | exit 0 | STK-RUST-06 |
| 7-9 | attestation checklist (one per rule) | explicit yes | STK-RUST-03, -07, -08 |

**Remediation:** fmt fail → `cargo fmt` · clippy `unwrap_used` fire → `?` with a typed
error, or `#[allow]` + `// INVARIANT:` if provable · clippy warning seems wrong → it
rarely is; read the lint's page before allowing · audit hit → `cargo update -p crate`
first; waive per-advisory with unreachability argument · ratchet fail → add tests for the
new code, don't lower the baseline.

## Worked Example

`examples/rust/` is the living example (an RPN calculator: `thiserror` lib +
`anyhow` bin). Minimal shape:

```
myproj/
├── Cargo.toml              # [lints] deny unwrap_used/expect_used (STK-RUST-03)
├── Cargo.lock              # committed (STK-RUST-06)
├── .coverage-baseline      # written by first ratchet run, committed
├── .env.example            # per SEC-SECRETS
├── src/lib.rs              # logic; thiserror error enum; #[cfg(test)] mod tests
└── src/main.rs             # thin anyhow::Result main over the lib
```

```toml
# Cargo.toml — the mechanical unwrap ban
[lints.clippy]
unwrap_used = "deny"
expect_used = "deny"
```

```rust
// src/lib.rs
#[derive(Debug, thiserror::Error, PartialEq)]
pub enum RpnError {
    #[error("unknown token {0:?}")]
    UnknownToken(String),
    #[error("division by zero")]
    DivideByZero,
}

// src/main.rs
fn main() -> anyhow::Result<()> {
    let expr = std::env::args().skip(1).collect::<Vec<_>>().join(" ");
    let value = rpn::eval(&expr).with_context(|| format!("evaluating {expr:?}"))?;
    println!("{value}");
    Ok(())
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `unwrap()` as error handling | Panics in production on the first surprise | `?` + typed errors (STK-RUST-03) |
| `Box<dyn Error>` in a library API | Callers can't match; type-erased at the boundary | `thiserror` enum (STK-RUST-03) |
| `anyhow` in a library's public API | Same erasure with better ergonomics | thiserror in libs, anyhow in bins |
| `clone()` to end a borrow fight | Hides a design problem, costs allocations | Restructure ownership; borrow or move |
| Blanket `#![allow(clippy::…)]` at crate root | Erases the signal permanently | Item-scoped `#[allow]` + reason (STK-RUST-02) |
| `.gitignore`-ing `Cargo.lock` in a library | CI and audit see different deps than users | Commit it (STK-RUST-06) |
| tokio for a sequential CLI | Async complexity tax with zero concurrency win | Sync code; add tokio when concurrency is real |
| Speculative workspace with one crate | Ceremony without a second crate to share | Single crate until real (STK-RUST-07) |

## References

- Rust API Guidelines (error types) + thiserror/anyhow docs — the split in STK-RUST-03.
- clippy lint index (`unwrap_used`, `expect_used`) — the mechanical ban's implementation.
- Cargo Book, `[lints]` table + FAQ on `Cargo.lock` — lint config and the updated
  commit-the-lockfile guidance (STK-RUST-06).
- RustSec / cargo-audit docs — the SCA backend for STK-RUST-05.
- cargo-llvm-cov README — LCOV emission consumed by the ratchet (STK-RUST-04).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
