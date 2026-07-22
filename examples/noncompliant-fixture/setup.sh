#!/usr/bin/env bash
# setup.sh — generate the deliberately NON-compliant fixture project into a target dir.
# Used by the Phase-4 negative test: /verify-compliance must FAIL on this project citing
# the exact rule IDs, and flip to progress when violations are fixed one by one.
#
# Violations planted:
#   1. SEC-SECRETS-01 — hardcoded AWS-style key in src (assembled here so this repo
#      itself never contains a matchable pattern)
#   2. STK-PY-03     — ruff violations (unused import, bad format)
#   3. STK-PY-04     — bandit B608 (f-string SQL)
#   4. STK-PY-02     — coverage below the committed .coverage-baseline
#   5. waiver        — expired waiver in GOVERNANCE.md
#
# Usage: setup.sh <target-dir> [--install]   (--install also creates .venv with dev tools)
set -euo pipefail

TARGET="${1:?usage: setup.sh <target-dir> [--install]}"
mkdir -p "$TARGET"/src/badproj "$TARGET"/tests
cd "$TARGET"

git init -q -b main 2>/dev/null || true

FAKE_KEY="AKIA$(printf 'IOSFODNN7BADFIXT')"   # assembled at generation time

cat > src/badproj/__init__.py <<EOF
import json  # unused: ruff F401
import sqlite3

AWS_KEY = "${FAKE_KEY}"  # SEC-SECRETS-01: hardcoded credential


def get_user(conn, user_id):
    # STK-PY anti-pattern / bandit B608: f-string SQL
    cur = conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cur.fetchone()


def untested_logic(x):
    # deliberately uncovered by tests -> coverage below baseline
    if x > 10:
        return "big"
    if x > 5:
        return "medium"
    return "small"
EOF

cat > tests/test_min.py <<'EOF'
import sys
sys.path.insert(0, "src")
from badproj import untested_logic


def test_small():
    assert untested_logic(1) == "small"
EOF

cat > pyproject.toml <<'EOF'
[project]
name = "badproj"
version = "0.0.1"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["src"]
EOF

echo "90.00" > .coverage-baseline

cat > GOVERNANCE.md <<'EOF'
# Governance Manifest

```yaml
tier: T2
classified: 2026-07-01
tier_override: null
stacks: [python, sqlite]
standards:
  - {id: SEC-SECRETS, version: 1.0.1}
  - {id: STK-PY, version: 1.0.1}
waivers:
  - {rule_id: STK-PY-05, reason: "fixture: expired waiver test", expires: 2026-07-10, granted: 2026-06-01, granted_by: James}
last_verified: null
attestations: []
```

## Notes

Deliberately noncompliant fixture — see examples/noncompliant-fixture/setup.sh.
EOF

printf '.venv/\n__pycache__/\n.env\n' > .gitignore
git add -A >/dev/null 2>&1 || true

if [[ "${2:-}" == "--install" ]]; then
  python3 -m venv .venv
  .venv/bin/pip -q install ruff bandit pytest pytest-cov pip-audit >/dev/null
fi

echo "noncompliant fixture generated at $(pwd)"
