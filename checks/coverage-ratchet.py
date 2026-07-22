#!/usr/bin/env python3
"""coverage-ratchet.py — coverage may never decrease (Constitution C3, TST-RATCHET).

Compares a current coverage percentage against the committed baseline file
`.coverage-baseline` in the project root. If coverage >= baseline, the baseline is
raised to the new value (ratchet up); if it's lower, exit 1.

Reads coverage from (first match wins):
  1. --value <float>            explicit percentage
  2. coverage.json              (pytest-cov / coverage.py:  totals.percent_covered)
  3. coverage/coverage-summary.json  (istanbul/vitest:  total.lines.pct)
  4. coverage.out               (go tool cover -func output, "total:" line)
  5. lcov.info                  (LH/LF aggregate)

Usage: python3 coverage-ratchet.py [--project DIR] [--value PCT] [--tolerance 0.1] [--check]
  --check  read-only: never writes the baseline (used by /verify-compliance so a
           verification run leaves no working-tree changes)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def read_coverage(root: Path) -> float | None:
    cj = root / "coverage.json"
    if cj.exists():
        return float(json.loads(cj.read_text())["totals"]["percent_covered"])
    cs = root / "coverage" / "coverage-summary.json"
    if cs.exists():
        return float(json.loads(cs.read_text())["total"]["lines"]["pct"])
    go = root / "coverage.out"
    if go.exists():
        import subprocess
        out = subprocess.run(["go", "tool", "cover", f"-func={go}"],
                             capture_output=True, text=True, cwd=root).stdout
        m = re.search(r"total:.*?([\d.]+)%", out)
        if m:
            return float(m.group(1))
    lcov = root / "lcov.info"
    if lcov.exists():
        lh = lf = 0
        for line in lcov.read_text().splitlines():
            if line.startswith("LH:"):
                lh += int(line[3:])
            elif line.startswith("LF:"):
                lf += int(line[3:])
        if lf:
            return 100.0 * lh / lf
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".", type=Path)
    ap.add_argument("--value", type=float, default=None)
    ap.add_argument("--tolerance", type=float, default=0.1,
                    help="allowed dip in percentage points (float noise)")
    ap.add_argument("--check", action="store_true",
                    help="read-only: never write/init the baseline")
    args = ap.parse_args()
    root = args.project.resolve()
    baseline_file = root / ".coverage-baseline"

    current = args.value if args.value is not None else read_coverage(root)
    if current is None:
        print("coverage-ratchet: no coverage data found (run tests with coverage first)")
        return 2

    if not baseline_file.exists():
        if args.check:
            print(f"coverage-ratchet: OK (no baseline yet; current {current:.2f}% — "
                  f"run without --check to initialize)")
            return 0
        baseline_file.write_text(f"{current:.2f}\n")
        print(f"coverage-ratchet: baseline initialized at {current:.2f}%")
        return 0

    baseline = float(baseline_file.read_text().strip())
    if current + args.tolerance < baseline:
        print(f"coverage-ratchet: FAIL — coverage {current:.2f}% is below baseline "
              f"{baseline:.2f}%. Add tests or (with a waiver) reset the baseline.")
        return 1
    if current > baseline and not args.check:
        baseline_file.write_text(f"{current:.2f}\n")
        print(f"coverage-ratchet: raised baseline {baseline:.2f}% → {current:.2f}%")
    else:
        print(f"coverage-ratchet: OK ({current:.2f}% ≥ {baseline:.2f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
