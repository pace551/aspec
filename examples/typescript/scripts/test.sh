#!/usr/bin/env bash
# test.sh — STK-TS-04 gate: vitest + coverage/coverage-summary.json (the format
# coverage-ratchet.py reads). The pre-push hook and the CI test job run this same
# script. --passWithNoTests tolerates a fresh scaffold — TST-POLICY governs test
# existence, not this script.
set -euo pipefail
cd "$(dirname "$0")/.."

node_modules/.bin/vitest run --coverage --passWithNoTests
