#!/usr/bin/env python3
"""Self-lint for the governance framework (Phase-4 check #1, run in framework CI).

Validates every standard against the schema contract in templates/standard-template.md:
frontmatter completeness, ID/filename discipline, rule extraction and enforcement backing,
requires resolution, changelog/version consistency, abstract length, index freshness.

Usage: python3 checks/lint-framework.py [FILE ...]
With FILE args: lint only those standards and skip the index-freshness check (used by
parallel authoring agents; the full run happens at merge). Exit 0 = clean; exit 1 =
violations (each printed with file and reason).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STANDARDS = ROOT / "standards"

FAMILIES = {"SEC", "TST", "ARC", "STK", "INF", "OPS", "DEV", "UX", "DATA", "AI", "LEG"}
TIER_VALUES = {"required", "advisory", "n/a"}
STATUSES = {"draft", "active", "deprecated"}
LAYERS = {"H", "G", "A"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ID_RE = re.compile(r"^[A-Z]+-[A-Z0-9]+$")
RULE_HEADING_RE = re.compile(r"^### ([A-Z]+-[A-Z0-9]+-\d{2}) — ", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_KEYS = [
    "id", "title", "family", "version", "status", "tiers", "stacks",
    "triggers", "requires", "verification", "last_review",
]
REQUIRED_SECTIONS = [
    "## Abstract", "## Normative Rules", "## Verification", "## Worked Example",
    "## Anti-Patterns", "## References", "## Changelog",
]


def lint_file(path: Path, all_ids: set[str]) -> list[str]:
    rel = str(path.relative_to(ROOT))
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return [f"{rel}: missing frontmatter"]
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return [f"{rel}: frontmatter YAML error: {exc}"]
    errs: list[str] = []
    body = text[m.end():]

    for key in REQUIRED_KEYS:
        if key not in meta:
            errs.append(f"{rel}: frontmatter missing `{key}`")
    sid = str(meta.get("id", ""))
    if not ID_RE.match(sid):
        errs.append(f"{rel}: bad id `{sid}`")
    if path.stem != sid.lower():
        errs.append(f"{rel}: filename should be `{sid.lower()}.md`")
    fam = str(meta.get("family", ""))
    if fam not in FAMILIES:
        errs.append(f"{rel}: unknown family `{fam}`")
    if sid and fam and not sid.startswith(fam + "-"):
        errs.append(f"{rel}: id `{sid}` does not start with family `{fam}-`")
    if not SEMVER_RE.match(str(meta.get("version", ""))):
        errs.append(f"{rel}: version `{meta.get('version')}` is not semver")
    if meta.get("status") not in STATUSES:
        errs.append(f"{rel}: bad status `{meta.get('status')}`")

    tiers = meta.get("tiers") or {}
    for t in ("T1", "T2", "T3", "T4"):
        if tiers.get(t) not in TIER_VALUES:
            errs.append(f"{rel}: tiers.{t} must be one of {sorted(TIER_VALUES)}")

    stacks = meta.get("stacks")
    if stacks != "all" and not (isinstance(stacks, list) and stacks):
        errs.append(f"{rel}: stacks must be `all` or a non-empty list")
    if not (isinstance(meta.get("triggers"), list) and meta["triggers"]):
        errs.append(f"{rel}: triggers must be a non-empty list")

    for req in meta.get("requires") or []:
        if req not in all_ids:
            errs.append(f"{rel}: requires unknown standard `{req}`")

    # Verification block
    verification = meta.get("verification") or []
    if not verification:
        errs.append(f"{rel}: verification must be non-empty (use a layer:A attestation "
                    f"entry for advisory-only standards)")
    verified_rules: set[str] = set()
    for i, v in enumerate(verification):
        if not isinstance(v, dict) or "cmd" not in v or "layer" not in v:
            errs.append(f"{rel}: verification[{i}] needs cmd/expect/layer")
            continue
        if v["layer"] not in LAYERS:
            errs.append(f"{rel}: verification[{i}] layer `{v['layer']}` not in H/G/A")
        verified_rules.update(v.get("rules") or [])

    # Rules
    rule_ids = RULE_HEADING_RE.findall(body)
    if not rule_ids:
        errs.append(f"{rel}: no normative rules found (### {sid}-NN — …)")
    seen: set[str] = set()
    for n, rid in enumerate(rule_ids, start=1):
        if rid in seen:
            errs.append(f"{rel}: duplicate rule id {rid}")
        seen.add(rid)
        if not rid.startswith(sid + "-"):
            errs.append(f"{rel}: rule {rid} does not match standard id {sid}")
        if rid != f"{sid}-{n:02d}":
            errs.append(f"{rel}: rule ids not contiguous — expected {sid}-{n:02d}, got {rid}")
    for vr in verified_rules:
        if vr not in seen:
            errs.append(f"{rel}: verification references unknown rule `{vr}`")

    # Enforcement backing: each rule whose block mentions `required` needs H/G
    # verification coverage or an explicit attestation marker.
    blocks = RULE_HEADING_RE.split(body)  # [pre, id1, block1, id2, block2, ...]
    for rid, block in zip(blocks[1::2], blocks[2::2]):
        tier_line = block.splitlines()[0] if block.splitlines() else ""
        first_para = "\n".join(block.splitlines()[:4])
        if "required" in tier_line and rid not in verified_rules \
                and "Layer**: A" not in first_para:
            errs.append(f"{rel}: required rule {rid} has no H/G verification and no "
                        f"explicit `**Layer**: A (attestation)` marker")

    # Sections & prose discipline
    for sec in REQUIRED_SECTIONS:
        if sec not in body:
            errs.append(f"{rel}: missing section `{sec}`")
    abstract = re.search(r"## Abstract\n+(.*?)\n## ", body, re.DOTALL)
    if abstract and len(abstract.group(1).split()) > 120:
        errs.append(f"{rel}: abstract over 120 words "
                    f"({len(abstract.group(1).split())})")
    version = str(meta.get("version", ""))
    changelog = body.split("## Changelog", 1)[-1]
    if version and f"**{version}**" not in changelog:
        errs.append(f"{rel}: changelog has no entry for current version {version}")
    return errs


def main() -> int:
    only = [Path(a).resolve() for a in sys.argv[1:]]
    files = sorted(STANDARDS.rglob("*.md"))
    all_ids: set[str] = set()
    for path in files:
        m = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
        if m:
            try:
                all_ids.add(str((yaml.safe_load(m.group(1)) or {}).get("id", "")))
            except yaml.YAMLError:
                pass

    errors: list[str] = []
    lint_targets = [p for p in files if not only or p.resolve() in only]
    for path in lint_targets:
        errors.extend(lint_file(path, all_ids))

    if only:
        # Partial mode: requires-resolution against not-yet-written IDs is expected
        # during parallel authoring; downgrade those to warnings.
        hard = [e for e in errors if "requires unknown standard" not in e]
        for w in (e for e in errors if e not in hard):
            print(f"  ⚠ (deferred) {w}")
        errors = hard
    else:
        # Index freshness (delegated to build-index --check)
        check = subprocess.run(
            [sys.executable, str(ROOT / "checks" / "build-index.py"), "--check"],
            capture_output=True, text=True,
        )
        if check.returncode != 0:
            errors.append(check.stdout.strip() or "index.json stale")
    files = lint_targets

    if errors:
        print(f"lint-framework: {len(errors)} violation(s)")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print(f"lint-framework: clean ({len(files)} standards)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
