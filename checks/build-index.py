#!/usr/bin/env python3
"""Generate index.json + INDEX.md from standards/ frontmatter.

Self-gate (Constitution C10): a standard whose content changed but whose version did not
bump refuses to index, and so does a version bump whose `last_review` neither moved later
nor is today (a same-day sweep then edit keeps today's date). The `last_review:` line is
left out of the hash, so the /evolve-standards staleness sweep can touch it alone without
a bump. Hashes live in checks/.index-hashes.json (committed).

Usage: build-index.py [--check] [--root DIR] [--today YYYY-MM-DD]
  --check     verify index.json is current without rewriting (used by lint/CI)
  --root DIR  framework root to index (default: this script's repo; tests use a temp tree)
  --today D   today's date, YYYY-MM-DD (default: the local date; tests pass a fixed one)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

FAMILY_NAMES = {
    "SEC": "Security",
    "TST": "Testing",
    "ARC": "Architecture",
    "STK": "Stacks",
    "INF": "Infrastructure",
    "OPS": "Operations",
    "DEV": "Process",
    "UX": "UI/UX",
    "DATA": "Data governance",
    "AI": "LLM concerns",
    "LEG": "Legal/commercial",
}

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
LAST_REVIEW_RE = re.compile(r"^last_review:[^\n]*\n", re.MULTILINE)


def parse_standard(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: no frontmatter block")
    meta = yaml.safe_load(m.group(1))
    if not isinstance(meta, dict):
        raise TypeError(f"{path}: frontmatter is not a mapping")
    return meta, text


ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def iso_date(value: str) -> date | None:
    """A YYYY-MM-DD string as a date, or None (date.fromisoformat alone also takes
    20261105 and 2026-W45-4)."""
    try:
        return date.fromisoformat(value) if ISO_DATE_RE.match(value) else None
    except ValueError:
        return None


def today_arg(value: str) -> str:
    if iso_date(value) is None:
        raise argparse.ArgumentTypeError(f"expected a YYYY-MM-DD date, got {value!r}")
    return value


def content_hash(text: str) -> str:
    """sha256 of the standard without its frontmatter `last_review:` line."""
    m = FRONTMATTER_RE.match(text)
    end = m.end() if m else 0
    text = LAST_REVIEW_RE.sub("", text[:end], count=1) + text[end:]
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def legacy_hash(text: str) -> str:
    """Whole-file sha256, as hashes were stored before `last_review` was recorded."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument(
        "--today",
        type=today_arg,
        default=datetime.now().astimezone().date().isoformat(),
    )
    args = ap.parse_args()
    # A UTC CI runner can be a day behind an author east of UTC: allow one day ahead.
    latest_review = (date.fromisoformat(args.today) + timedelta(days=1)).isoformat()
    check_only = args.check
    root = args.root.resolve()
    standards = root / "standards"
    hashes_path = root / "checks" / ".index-hashes.json"
    index_json = root / "index.json"
    index_md = root / "INDEX.md"
    errors: list[str] = []
    entries: list[dict] = []
    new_hashes: dict[str, dict] = {}
    old_hashes = json.loads(hashes_path.read_text()) if hashes_path.exists() else {}

    for path in sorted(standards.rglob("*.md")):
        try:
            meta, text = parse_standard(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        sid = meta.get("id", "")
        version = str(meta.get("version", ""))
        last_review = str(meta.get("last_review", ""))
        digest = content_hash(text)
        rel = path.relative_to(root)
        dated = iso_date(last_review) is not None
        if not dated:
            errors.append(f"{rel}: last_review {last_review!r} is not a YYYY-MM-DD date (C10)")
        elif last_review > latest_review:
            errors.append(
                f"{rel}: last_review {last_review} is after today ({args.today}) — a review "
                "date can't be in the future (C10)"
            )
        prior = old_hashes.get(sid)
        if prior and dated:
            legacy = "last_review" not in prior
            changed = prior["hash"] != (legacy_hash(text) if legacy else digest)
            if changed and prior["version"] == version:
                errors.append(
                    f"{rel}: content changed but version still "
                    f"{version} — bump `version` and add a Changelog entry (C10)"
                )
            # ISO dates order as strings. A bump must date its review: later than the
            # indexed one, or today (a sweep may already have set today's date).
            indexed = prior.get("last_review", "")
            # same-day edits keep the indexed date when it is today (or the day's slack)
            same_day = last_review == indexed and args.today <= indexed <= latest_review
            reviewed = legacy or last_review > indexed or same_day
            if prior["version"] != version and not reviewed:
                errors.append(
                    f"{rel}: version changed to {version} but "
                    f"last_review {last_review} isn't later than the indexed "
                    f"{prior['last_review']} — set it to today's date (C10)"
                )
        new_hashes[sid] = {"version": version, "hash": digest, "last_review": last_review}
        entries.append(
            {
                "id": sid,
                "title": meta.get("title", ""),
                "family": meta.get("family", ""),
                "version": version,
                "status": meta.get("status", ""),
                "tiers": meta.get("tiers", {}),
                "published": meta.get("published", "n/a"),
                "stacks": meta.get("stacks", "all"),
                "triggers": meta.get("triggers", []),
                "requires": meta.get("requires", []),
                "verification_layers": sorted(
                    {v.get("layer", "?") for v in (meta.get("verification") or [])}
                ),
                "last_review": last_review,
                "path": str(path.relative_to(root)),
                "tokens_est": len(text) // 4,
            }
        )

    dupes = {e["id"] for e in entries if sum(x["id"] == e["id"] for x in entries) > 1}
    for d in sorted(dupes):
        errors.append(f"duplicate standard id: {d}")

    if errors:
        print("build-index: REFUSED\n" + "\n".join(f"  ✗ {e}" for e in errors))
        return 1

    index = {
        "schema": 1,
        "generated": args.today,
        "constitution": ["constitution/CONSTITUTION.md", "constitution/tiers.md"],
        "standards": entries,
    }
    payload = json.dumps(index, indent=2, sort_keys=False) + "\n"

    if check_only:
        if not index_json.exists():
            print("build-index --check: index.json missing")
            return 1
        current = json.loads(index_json.read_text())
        current["generated"] = index["generated"]  # date alone is not staleness
        if current != index:
            print("build-index --check: index.json is stale — run checks/build-index.py")
            return 1
        print(f"build-index --check: current ({len(entries)} standards)")
        return 0

    index_json.write_text(payload, encoding="utf-8")
    hashes_path.write_text(json.dumps(new_hashes, indent=2, sort_keys=True) + "\n")

    lines = [
        "# Standards Index",
        "",
        f"Generated by `checks/build-index.py` — do not edit. {len(entries)} standards.",
        "",
    ]
    for fam, fam_name in FAMILY_NAMES.items():
        fam_entries = [e for e in entries if e["family"] == fam]
        if not fam_entries:
            continue
        lines += [f"## {fam} — {fam_name} ({len(fam_entries)})", ""]
        lines.append("| ID | Title | Version | Status | T1 | T2 | T3 | T4 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for e in sorted(fam_entries, key=lambda x: x["id"]):
            t = e["tiers"]
            lines.append(
                f"| [{e['id']}]({e['path']}) | {e['title']} | {e['version']} "
                f"| {e['status']} | {t.get('T1', '?')} | {t.get('T2', '?')} "
                f"| {t.get('T3', '?')} | {t.get('T4', '?')} |"
            )
        lines.append("")
    index_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"build-index: wrote index.json + INDEX.md ({len(entries)} standards)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
