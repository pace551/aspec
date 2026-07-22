#!/usr/bin/env bash
# install-git-hooks.sh — run from a project root (done by /bootstrap-repo).
# Copies the _common hooks into .githooks/, vendors the governance check scripts into
# .governance/, and points git at them. Idempotent.
set -euo pipefail

GOV="${GOVERNANCE_DIR:-$HOME/Dev/claude-code/governance}"
COMMON="$GOV/templates/scaffolds/_common"

[ -d .git ] || { echo "install-git-hooks: run from a git repo root" >&2; exit 2; }

mkdir -p .githooks .governance
cp "$COMMON/githooks/pre-commit" "$COMMON/githooks/pre-push" .githooks/
cp "$GOV/checks/secret-scan.sh" "$GOV/checks/coverage-ratchet.py" .governance/
chmod +x .githooks/* .governance/secret-scan.sh
git config core.hooksPath .githooks

echo "install-git-hooks: installed (.githooks + vendored .governance from $GOV)"
