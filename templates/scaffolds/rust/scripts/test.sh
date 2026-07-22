#!/usr/bin/env bash
# test.sh — STK-RUST-04 gate: cargo test + lcov.info (the format coverage-ratchet.py
# reads), via cargo-llvm-cov (which itself runs the test suite). The pre-push hook
# and the CI test job run this same script. Missing cargo-llvm-cov degrades LOUDLY
# to plain `cargo test` — tests still gate, coverage emission is skipped visibly.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v cargo-llvm-cov >/dev/null 2>&1; then
  cargo llvm-cov --all-targets --lcov --output-path lcov.info
  cargo llvm-cov report --summary-only
else
  echo "test.sh: cargo-llvm-cov not installed — running tests WITHOUT coverage emission" >&2
  echo "test.sh: install with: cargo install cargo-llvm-cov (the ratchet needs lcov.info)" >&2
  cargo test
fi
