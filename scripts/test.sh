#!/usr/bin/env bash
# test.sh — the framework's test gate, run by the pre-push hook and the CI test job.
# pytest runs the unittest-style tests in checks/ (STK-PY-02) and writes coverage.json for
# the ratchet (TST-RATCHET); subprocess-run scripts are measured too (pyproject.toml).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/venv.sh

.venv/bin/pytest -q --cov --cov-report=json --cov-report=term
