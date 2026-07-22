#!/usr/bin/env bash
# lint.sh — scripts contract (format check + lint + types). Same gate as the
# pre-commit hook and the CI lint/typecheck jobs (STK-VITE-08).
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d node_modules ] || {
  echo "lint.sh: node_modules missing — run: npm ci (or npm install)" >&2
  exit 2
}

npx prettier --check .
npx eslint .
npx tsc --noEmit
