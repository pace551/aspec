#!/usr/bin/env bash
# lint.sh — STK-TS-03 gate. The pre-commit hook and the CI lint job run this same
# script (scripts contract, _common/README.md). Tools by node_modules/.bin path,
# never global installs (STK-TS-08).
set -euo pipefail
cd "$(dirname "$0")/.."

node_modules/.bin/prettier --check .
node_modules/.bin/eslint .
