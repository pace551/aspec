#!/usr/bin/env bash
# lint.sh — STK-PY-03 gate. The pre-commit hook and the CI lint job run this same
# script (scripts contract, _common/README.md). Tools by venv path, never activation
# (STK-PY-08).
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/ruff format --check . && .venv/bin/ruff check .
