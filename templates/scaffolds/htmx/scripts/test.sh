#!/usr/bin/env bash
# test.sh — scripts contract (tests + coverage emit). Same gate as pre-push hook and CI.
# Emits coverage.json for the ratchet (TST-RATCHET). Exit 5 ("no tests collected") is
# tolerated so a fresh scaffold is green; TST-POLICY governs test existence.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -x .venv/bin/pytest ] || {
  echo "test.sh: .venv missing — python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
  exit 2
}

rc=0
.venv/bin/pytest -q --cov=src --cov-report=json --cov-report=term || rc=$?
[ "$rc" -eq 0 ] || [ "$rc" -eq 5 ]
