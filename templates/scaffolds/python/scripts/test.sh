#!/usr/bin/env bash
# test.sh — STK-PY-02 gate: pytest + coverage.json (the format coverage-ratchet.py
# reads). The pre-push hook and the CI test job run this same script. Exit 5 ("no
# tests collected") is tolerated so a fresh scaffold isn't blocked — TST-POLICY
# governs test existence, not this script.
set -euo pipefail
cd "$(dirname "$0")/.."

rc=0
.venv/bin/pytest --cov --cov-report=json --cov-report=term || rc=$?
[ "$rc" -eq 0 ] || [ "$rc" -eq 5 ]
