#!/usr/bin/env python3
"""select-standards.py — deterministic standard selection for /govern (ADR-0003).

Filters index.json without ever loading it into agent context. Selection semantics:
  - status must be `active`
  - tier applicability `n/a` → excluded
  - stack-scoped standards match when their stacks intersect the project's
  - `required` at the tier → selected (stack permitting)
  - `advisory` at the tier → selected only when a trigger keyword matches the brief
  - transitive `requires` pulled in, capped at two hops

Usage:
  select-standards.py --tier T1 --stacks python,sqlite --brief-text "words of the task"
                      [--rules] [--governance-dir DIR]

Output: JSON to stdout — {selected: [...], token_estimate, excluded_count}.
With --rules, each entry also carries its normative rule list (id, statement, tiers,
layer) parsed from the doc, so /govern can emit a compliance brief without loading docs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RULE_RE = re.compile(
    r"^### ([A-Z]+-[A-Z0-9]+-\d{2}) — (.+?)\n+\*\*Tiers\*\*: (.+?) — \*\*Layer\*\*: (.+?)$",
    re.MULTILINE,
)


def load_rules(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    return [
        {"rule": m[0], "statement": m[1].strip(), "tiers": m[2].strip(),
         "layer": m[3].strip()}
        for m in RULE_RE.findall(text)
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=["T1", "T2", "T3", "T4"])
    ap.add_argument("--stacks", default="", help="comma-separated stack keys")
    ap.add_argument("--brief-text", default="", help="task description for trigger matching")
    ap.add_argument("--rules", action="store_true", help="include parsed rules per standard")
    ap.add_argument("--governance-dir",
                    default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()

    gov = Path(args.governance_dir)
    index = json.loads((gov / "index.json").read_text())
    stacks = {s.strip() for s in args.stacks.split(",") if s.strip()}
    brief = args.brief_text.lower()

    by_id = {e["id"]: e for e in index["standards"]}
    selected: dict[str, dict] = {}

    for e in index["standards"]:
        if e["status"] != "active":
            continue
        applicability = e["tiers"].get(args.tier, "n/a")
        if applicability == "n/a":
            continue
        stack_ok = e["stacks"] == "all" or bool(set(e["stacks"]) & stacks)
        if not stack_ok:
            continue
        triggered = [t for t in e["triggers"] if t in brief]
        if applicability == "required" or triggered:
            selected[e["id"]] = {
                "id": e["id"], "version": e["version"], "path": e["path"],
                "title": e["title"], "applicability": applicability,
                "matched_on": "required" if applicability == "required"
                else f"triggers: {', '.join(triggered)}",
                "tokens_est": e.get("tokens_est", 0),
            }

    # transitive requires, two hops max
    frontier = list(selected)
    for _hop in range(2):
        pulled = []
        for sid in frontier:
            for req in by_id.get(sid, {}).get("requires", []):
                if req not in selected and req in by_id:
                    e = by_id[req]
                    if e["status"] != "active":
                        continue
                    selected[req] = {
                        "id": req, "version": e["version"], "path": e["path"],
                        "title": e["title"],
                        "applicability": e["tiers"].get(args.tier, "advisory"),
                        "matched_on": f"required-by {sid}",
                        "tokens_est": e.get("tokens_est", 0),
                    }
                    pulled.append(req)
        frontier = pulled
        if not frontier:
            break

    if args.rules:
        for entry in selected.values():
            entry["rules"] = load_rules(gov / entry["path"])

    out = {
        "tier": args.tier,
        "stacks": sorted(stacks),
        "selected": sorted(selected.values(), key=lambda x: x["id"]),
        "token_estimate": sum(e["tokens_est"] for e in selected.values()),
        "excluded_count": len(index["standards"]) - len(selected),
    }
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
