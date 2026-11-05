#!/usr/bin/env bash
# lint.sh — the framework's lint gate, run by the pre-commit hook and the CI lint job:
# framework self-lint, ruff with the house config (STK-PY-03), and shell syntax.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/venv.sh

.venv/bin/python checks/lint-framework.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
bash -n checks/*.sh hooks/*.sh templates/scaffolds/_common/install-git-hooks.sh \
  templates/scaffolds/_common/githooks/* scripts/*.sh
