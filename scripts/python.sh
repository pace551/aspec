# python.sh — sourced by lint.sh/test.sh. Sets $PY to the newest python3 on PATH that is
# >= 3.11 (checks/ uses 3.11 APIs; CI runs 3.12) and can import PyYAML (lint-framework and
# the tests need it). Packages are per interpreter, so a newer Python without PyYAML is
# skipped for an older one that has it. Plain `python3` can be older, e.g. 3.9 on macOS.
PY=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null &&
     "$candidate" -c 'import sys, yaml; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PY=$candidate
    break
  fi
done
if [ -z "$PY" ]; then
  echo "scripts: need Python 3.11+ with PyYAML on PATH (pip install pyyaml)" >&2
  exit 2
fi
