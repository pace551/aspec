#!/usr/bin/env bash
# lint.sh — the framework's lint gate, run by the pre-commit hook. Same steps as the
# self-lint job in .github/workflows/framework.yml, minus the unit tests (scripts/test.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/python.sh

"$PY" checks/lint-framework.py
if [ "$(ruff --version 2>/dev/null)" = "ruff 0.17.1" ]; then
  RUFF=(ruff)
else
  RUFF=(uvx ruff@0.17.1)   # the version framework CI pins
fi
"${RUFF[@]}" check checks/          # house config in pyproject.toml (STK-PY-03)
"${RUFF[@]}" format --check checks/
bash -n checks/*.sh hooks/*.sh templates/scaffolds/_common/install-git-hooks.sh \
  templates/scaffolds/_common/githooks/* scripts/*.sh
