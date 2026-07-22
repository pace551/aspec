# Scaffold: rust (STK-RUST)

Copied by `/bootstrap-repo` for new Rust projects. On copy, bootstrap:

1. Fills `{{PROJECT_NAME}}` / `{{ONE_LINE_DESCRIPTION}}` in `Cargo.toml` and fixes the
   lib import in `src/main.rs`.
2. Layers in `_common/` (CLAUDE.md.seed → `CLAUDE.md`, GOVERNANCE.md.seed →
   `GOVERNANCE.md`, appends `gitignore-base` to `.gitignore`, installs git hooks via
   `install-git-hooks.sh`).
3. Runs `cargo build` (commit `Cargo.lock` — STK-RUST-06).

Layout is lib + thin bin in one crate (STK-RUST-07): logic in `src/lib.rs` with typed
`thiserror` errors, `src/main.rs` an `anyhow` shim over it (STK-RUST-03). The Cargo
`[lints]` table denies `unwrap()`/`expect()`; test modules opt out with an inner
`#![allow(...)]`.

Scripts contract (`_common/README.md`): hooks, CI (`templates/ci/rust.yml`), and
`/verify-compliance` all run `scripts/lint.sh` and `scripts/test.sh`. Coverage needs
`cargo install cargo-llvm-cov`; SCA needs `cargo install cargo-audit` (both fail/warn
loudly when missing, never silently).

Worked example built from this scaffold: `examples/rust/`.
