#!/usr/bin/env bash
# test.sh — scripts contract (tests + coverage emit). Same gate as the pre-push hook
# and the CI test job. Emits coverage/coverage-summary.json for the ratchet
# (TST-RATCHET). --passWithNoTests keeps a fresh scaffold green (STK-VITE-08).
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d node_modules ] || {
  echo "test.sh: node_modules missing — run: npm ci (or npm install)" >&2
  exit 2
}

npx vitest run --coverage --passWithNoTests
