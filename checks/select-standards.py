#!/usr/bin/env python3
"""select-standards.py — deterministic standard selection for /govern (ADR-0003).

Filters index.json without ever loading it into agent context. Selection semantics:
  - status must be `active`
  - tier applicability `n/a` → excluded
  - stack-scoped standards match when their stacks intersect the project's
  - `required` at the tier → selected (stack permitting)
  - `advisory` at the tier → selected only when a trigger keyword matches the brief
  - transitive `requires` pulled in, capped at two hops

Two modes (--mode):
  pins   (default) everything applicable at the tier — feeds GOVERNANCE.md pins; all of
         it is enforced by /verify-compliance whether or not it was in context.
  brief  the in-context subset: rule-level detail ONLY for stack-scoped matches,
         trigger matches, their requires closure, and the always-on core
         (SEC-SECRETS, TST-VERIFY, DEV-GIT); every other applicable standard appears
         as an id+title one-liner. This is what keeps T3/T4 intakes inside the ~15k
         token budget (ADR-0003).

Usage:
  select-standards.py --tier T1 --stacks python,sqlite --brief-text "words of the task"
                      [--mode pins|brief] [--rules] [--governance-dir DIR]

Output: JSON to stdout — pins: {selected, token_estimate, excluded_count};
brief: {detailed (with rules), listed, context_tokens}.
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
    ap.add_argument("--mode", choices=["pins", "brief"], default="pins")
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

    if args.mode == "brief":
        core = {"SEC-SECRETS", "TST-VERIFY", "DEV-GIT"}
        detailed_ids = set()
        for sid, entry in selected.items():
            e = by_id[sid]
            stack_scoped = e["stacks"] != "all" and bool(set(e["stacks"]) & stacks)
            triggered = entry["matched_on"].startswith("triggers")
            pulled = entry["matched_on"].startswith("required-by")
            if stack_scoped or triggered or pulled or sid in core:
                detailed_ids.add(sid)
        detailed, listed = [], []
        for sid, entry in sorted(selected.items()):
            if sid in detailed_ids:
                entry["rules"] = load_rules(gov / entry["path"])
                detailed.append(entry)
            else:
                listed.append({"id": sid, "title": entry["title"],
                               "applicability": entry["applicability"]})
        out = {
            "tier": args.tier,
            "stacks": sorted(stacks),
            "detailed": detailed,
            "listed": listed,
            "note": "ALL standards above are pinned+enforced; `listed` ones load on "
                    "demand while working in their area (/verify-compliance runs them "
                    "regardless).",
        }
        payload = json.dumps(out, indent=2)
        out["context_tokens"] = len(payload) // 4
        json.dump(out, sys.stdout, indent=2)
        print()
        return 0

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
