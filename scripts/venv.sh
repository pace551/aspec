# venv.sh — sourced by lint.sh/test.sh. Tools run from the project .venv by path, never by
# activation (STK-PY-08); the toolchain is pinned in pyproject.toml's dev dependency group.
if [ ! -x .venv/bin/python ]; then
  echo "scripts: .venv missing — create it with Python 3.11+:" >&2
  echo "  python3.14 -m venv .venv && .venv/bin/pip install --group dev" >&2
  exit 2
fi
