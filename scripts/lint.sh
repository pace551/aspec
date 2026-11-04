#!/usr/bin/env bash
# lint.sh — the framework's lint gate, run by the pre-commit hook. Same steps as the
# self-lint job in .github/workflows/framework.yml, minus the unit tests (scripts/test.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/python.sh

"$PY" checks/lint-framework.py
if [ "$(ruff --version 2>/dev/null)" = "ruff 0.17.1" ]; then
  ruff check checks/
else
  uvx ruff@0.17.1 check checks/   # the version framework CI pins
fi
bash -n checks/*.sh hooks/*.sh templates/scaffolds/_common/install-git-hooks.sh \
  templates/scaffolds/_common/githooks/* scripts/*.sh
