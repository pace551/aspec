#!/usr/bin/env python3
"""run-verification.py — deterministic executor behind /verify-compliance.

Reads the project's GOVERNANCE.md YAML block, resolves each pinned standard in the
governance repo, filters verification entries by the project tier, executes H/G commands
from the project root, and emits the attestation checklist for layer-A entries. Waived
rule IDs are skipped (expired waivers FAIL). Exit 0 only when every required H/G command
passes and no waiver is expired.

Usage:
  run-verification.py [--project DIR] [--governance-dir DIR] [--json] [--stamp]
    --stamp   on full pass, write last_verified: <today> into GOVERNANCE.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def read_manifest(project: Path) -> tuple[dict, str, Path]:
    gpath = project / "GOVERNANCE.md"
    if not gpath.exists():
        sys.exit("run-verification: no GOVERNANCE.md — run /govern first")
    text = gpath.read_text(encoding="utf-8")
    m = YAML_BLOCK_RE.search(text)
    if not m:
        sys.exit("run-verification: GOVERNANCE.md has no ```yaml block")
    return yaml.safe_load(m.group(1)), text, gpath


def find_standard(gov: Path, sid: str) -> dict | None:
    for path in (gov / "standards").rglob(f"{sid.lower()}.md"):
        m = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
        if m:
            return yaml.safe_load(m.group(1))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".", type=Path)
    ap.add_argument("--governance-dir",
                    default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stamp", action="store_true")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()
    project = args.project.resolve()
    gov = Path(args.governance_dir)

    manifest, gtext, gpath = read_manifest(project)
    tier = manifest.get("tier")
    if tier not in ("T1", "T2", "T3", "T4"):
        sys.exit(f"run-verification: bad tier {tier!r} in GOVERNANCE.md")

    today = date.today().isoformat()
    waived: set[str] = set()
    results: list[dict] = []
    attestations: list[dict] = []
    failures = 0

    for w in manifest.get("waivers") or []:
        expires = str(w.get("expires", ""))
        if not expires:
            results.append({"kind": "waiver", "id": w.get("rule_id", "?"),
                            "status": "FAIL", "detail": "waiver missing expiry"})
            failures += 1
            continue
        if expires < today:
            results.append({"kind": "waiver", "id": w.get("rule_id", "?"),
                            "status": "FAIL", "detail": f"waiver expired {expires}"})
            failures += 1
        else:
            waived.add(str(w.get("rule_id")))
            note = "ok"
            if (date.fromisoformat(expires) - date.today()).days <= 14:
                note = f"expires soon ({expires})"
            results.append({"kind": "waiver", "id": w.get("rule_id"),
                            "status": "WAIVED", "detail": note})

    for pin in manifest.get("standards") or []:
        sid, pinned_ver = pin.get("id"), str(pin.get("version", ""))
        meta = find_standard(gov, sid)
        if meta is None:
            results.append({"kind": "standard", "id": sid, "status": "FAIL",
                            "detail": "standard not found in governance repo"})
            failures += 1
            continue
        if str(meta.get("version")) != pinned_ver:
            results.append({"kind": "standard", "id": sid, "status": "WARN",
                            "detail": f"pinned {pinned_ver}, repo has "
                                      f"{meta.get('version')} — /govern offers upgrades"})
        for v in meta.get("verification") or []:
            vtiers = v.get("tiers")
            if vtiers and tier not in vtiers:
                continue
            rules = [str(r) for r in (v.get("rules") or [])]
            if rules and set(rules) <= waived:
                results.append({"kind": "check", "id": ",".join(rules), "std": sid,
                                "status": "WAIVED", "detail": v["cmd"][:80]})
                continue
            if str(v["cmd"]).startswith("attest: "):
                attestations.append({"standard": sid, "rules": rules,
                                     "item": str(v["cmd"])[8:]})
                continue
            proc = subprocess.run(
                ["bash", "-c", str(v["cmd"])], cwd=project, text=True,
                capture_output=True, timeout=args.timeout,
            )
            ok = proc.returncode == 0
            if not ok:
                failures += 1
            results.append({
                "kind": "check", "std": sid, "id": ",".join(rules) or sid,
                "layer": v.get("layer"), "status": "PASS" if ok else "FAIL",
                "detail": str(v["cmd"])[:100],
                "output": "" if ok else (proc.stdout + proc.stderr)[-1500:],
                "expect": v.get("expect", ""),
            })

    passed = failures == 0
    if passed and args.stamp:
        new_yaml = re.sub(r"last_verified:.*", f"last_verified: {today}",
                          YAML_BLOCK_RE.search(gtext).group(1))
        gpath.write_text(gtext.replace(YAML_BLOCK_RE.search(gtext).group(1), new_yaml),
                         encoding="utf-8")

    report = {"tier": tier, "passed": passed, "failures": failures,
              "results": results, "attestations_pending": attestations}
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print(f"verify-compliance · tier {tier} · "
              f"{'PASS' if passed else f'FAIL ({failures})'}")
        for r in results:
            line = f"  [{r['status']:>6}] {r.get('std', '')} {r['id']} — {r['detail']}"
            print(line)
            if r.get("output"):
                for ln in r["output"].strip().splitlines()[-8:]:
                    print(f"           | {ln}")
        if attestations:
            print(f"  attestations pending ({len(attestations)}) — "
                  f"/verify-compliance records these in GOVERNANCE.md:")
            for a in attestations:
                print(f"    [{a['rules'][0] if a['rules'] else '?'}] {a['item']}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
