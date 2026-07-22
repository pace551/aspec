#!/usr/bin/env bash
# lint.sh — scripts contract (format check + lint). Same gate as pre-commit hook and CI.
# STK-PY house tooling, invoked by venv path (STK-PY-08).
set -euo pipefail
cd "$(dirname "$0")/.."

[ -x .venv/bin/ruff ] || {
  echo "lint.sh: .venv missing — python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
  exit 2
}

.venv/bin/ruff check .
.venv/bin/ruff format --check .
