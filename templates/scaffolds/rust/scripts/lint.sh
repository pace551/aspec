#!/usr/bin/env bash
# lint.sh — STK-RUST-01/-02 gate. The pre-commit hook and the CI lint job run this
# same script (scripts contract, _common/README.md). Warnings are errors; the Cargo
# [lints] table makes clippy also enforce the unwrap/expect ban (STK-RUST-03).
set -euo pipefail
cd "$(dirname "$0")/.."

cargo fmt --check
cargo clippy --all-targets -- -D warnings
