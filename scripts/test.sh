#!/usr/bin/env bash
# test.sh — the framework's test gate, run by the pre-push hook. Same as the unit-test
# step of the self-lint job in .github/workflows/framework.yml.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/python.sh

"$PY" -m unittest discover -s checks -p "test_*.py"
