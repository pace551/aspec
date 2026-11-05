#!/usr/bin/env python3
"""Self-lint for the governance framework (Phase-4 check #1, run in framework CI).

Validates every standard against the schema contract in templates/standard-template.md:
frontmatter completeness, ID/filename discipline, rule extraction and enforcement backing,
requires resolution, changelog/version consistency, abstract length, index freshness,
no hardcoded home/absolute paths into the governance repo.

Usage: python3 checks/lint-framework.py [FILE ...]
With FILE args: lint only those standards and skip the index-freshness check (used by
parallel authoring agents; the full run happens at merge). Exit 0 = clean; exit 1 =
violations (each printed with file and reason).
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess  # nosec B404 - argv-only subprocess use, audited below
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STANDARDS = ROOT / "standards"

FAMILY_DIRS = {
    "SEC": "security",
    "TST": "testing",
    "ARC": "architecture",
    "STK": "stacks",
    "INF": "infra",
    "OPS": "operations",
    "DEV": "process",
    "UX": "ux",
    "DATA": "data",
    "AI": "ai",
    "LEG": "legal",
}
FAMILIES = set(FAMILY_DIRS)
STACK_KEYS = set(json.loads((ROOT / "checks" / "stack-keys.json").read_text()))
TIER_VALUES = {"required", "advisory", "n/a"}
TIER_NAMES = {"T1", "T2", "T3", "T4"}
PUBLISHED_FAMILIES = {"SEC", "TST", "DEV", "LEG"}
TIER_LINE_RE = re.compile(r"^\*\*Tiers\*\*: (.+?) — \*\*Layer\*\*: (.+)$", re.MULTILINE)
STATUSES = {"draft", "active", "deprecated"}
LAYERS = {"H", "G", "A"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ID_RE = re.compile(r"^[A-Z]+-[A-Z0-9]+$")
RULE_HEADING_RE = re.compile(r"^### ([A-Z]+-[A-Z0-9]+-\d{2}) — ", re.MULTILINE)
HOME_PATH_RE = re.compile(r"(~|\$HOME|\$\{HOME\}|/Users/[^/\s]+|/home/[^/\s]+)/")
GOV_PATH_RE = re.compile(
    r"(?:~|\$HOME|\$\{HOME\}|/Users/[^/\s]+|/home/[^/\s]+)"
    r"/\S*?/(?:checks|hooks|templates)/"
)
ABS_GOV_PATH_RE = re.compile(
    r"(?<![\w}$.~:/-])/(?:[^\s\"'`/]+/)*"
    r"(?:(?:checks|hooks)/[\w.-]+\.(?:sh|py)\b|templates/(?:scaffolds|ci)/)"
)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_KEYS = [
    "id",
    "title",
    "family",
    "version",
    "status",
    "tiers",
    "stacks",
    "triggers",
    "requires",
    "verification",
    "last_review",
]
REQUIRED_SECTIONS = [
    "## Abstract",
    "## Normative Rules",
    "## Verification",
    "## Worked Example",
    "## Anti-Patterns",
    "## References",
    "## Changelog",
]


def hardcoded_cmd_path(cmd: str) -> bool:
    return bool(HOME_PATH_RE.search(cmd) or ABS_GOV_PATH_RE.search(cmd))


def hardcoded_body_path(body: str) -> bool:
    return bool(GOV_PATH_RE.search(body) or ABS_GOV_PATH_RE.search(body))


# A framework script (the governance repo's checks/) launched by a bare python/python3,
# which runs on whatever interpreter is first on PATH (an end-of-life 3.9 on macOS). It
# must go through the repo's .venv: "$GOVERNANCE_DIR/.venv/bin/python" (or $GOV in skills),
# which checks/install.sh builds with Python 3.11+. A project's vendored copy
# (.governance/...) runs on the project's own Python and isn't matched.
BARE_PYTHON_RE = re.compile(
    r"(?<![/\w.])python3?(?:\.\d+)?\s+[\"']?\$\{?(?:GOVERNANCE_DIR|GOV)\}?/checks/[\w-]+\.py"
)


def bare_python_launch(text: str) -> bool:
    return bool(BARE_PYTHON_RE.search(text))


# Plain xargs splits its input on whitespace, so a path with a space becomes two
# nonexistent paths and the check silently passes (or finds nothing). File lists go to
# xargs NUL-separated: the producer emits NULs (`-print0`, `--null`, `-z`, `-0`) and
# xargs reads them with `-0`/`--null`. Only piped xargs (`| xargs`, also across a `\`
# line continuation) is checked, so prose that names xargs isn't. Options are parsed by
# arity (GNU + BSD), so `-n 1 -0` is NUL-safe while `-P0`/`-I0` (a value of 0) are not.
XARGS_RE = re.compile(r"\|\s*(?:\\\n\s*)?xargs(?![\w-])([^\n|;&`'\"()]*)")
XARGS_SHORT_WITH_ARG = set("adEILnPsJRS")  # value attached or as the next word
XARGS_SHORT_OPTIONAL_ARG = set("eil")  # GNU: value only when attached
XARGS_LONG_WITH_ARG = {
    "--arg-file",
    "--delimiter",
    "--max-args",
    "--max-chars",
    "--max-lines",
    "--max-procs",
    "--process-slot-var",
}


def xargs_reads_nul(args: list[str]) -> bool:
    """True when xargs' own options (before the command it runs) include -0/--null."""
    i = 0
    while i < len(args):
        tok = args[i]
        i += 1
        if tok == "--" or not tok.startswith("-") or tok == "-":
            return False  # end of options: the command starts here
        if tok.startswith("--"):
            name = tok.split("=", 1)[0]
            if name == "--null":
                return True
            if "=" not in tok and name in XARGS_LONG_WITH_ARG:
                i += 1
            continue
        for j, ch in enumerate(tok[1:], 1):
            if ch == "0":
                return True
            if ch in XARGS_SHORT_WITH_ARG:
                if j == len(tok) - 1:
                    i += 1  # the value is the next word
                break
            if ch in XARGS_SHORT_OPTIONAL_ARG:
                break
    return False


def unsafe_xargs(text: str) -> bool:
    return any(not xargs_reads_nul(m.group(1).split()) for m in XARGS_RE.finditer(text))


# A framework file named where users and agents read about it: checks/, templates/ or
# skills/, bare, after $GOV/ / $GOVERNANCE_DIR/ (quoted or not), or as a relative link
# (../checks/x). Not inside a URL or another project path.
REF_RE = re.compile(
    r"(?<![\w./$-])"
    r"(?P<prefix>\$\{?GOV(?:ERNANCE_DIR)?\}?\"?/|(?:\.\./)+)?"
    r"(?P<ref>(?:checks|templates|skills)/[\w.\-/]+)"
    r"(?P<tail>[*?\[{<][\w.*?\[\]\-/{}<>]*)?"
)
ADR_RE = re.compile(r"\bADR-(\d{4})\b")
CODE_RE = re.compile(r"<(code|pre)>(.*?)</\1>|```(.*?)```|`([^`\n]+)`", re.DOTALL)
PIP_INSTALL_RE = re.compile(r"\bpip3?\s+install\b(.*)")
PEP508_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]*\])?(?:[<>=!~].*)?$")
PIP_VALUE_FLAGS = {
    "-r", "--requirement", "-c", "--constraint", "--group", "-e", "--editable",
    "-i", "--index-url", "--extra-index-url", "-t", "--target", "--prefix", "-f",
    "--find-links",
}  # fmt: skip


def reference_files(root: Path) -> list[Path]:
    """Where framework paths are named for readers: skills, docs, standards, the
    constitution, templates' prose, README and CLAUDE.md."""
    files = [*(root / "skills").rglob("*.md"), *(root / "standards").rglob("*.md")]
    files += [*(root / "constitution").rglob("*.md"), *(root / "templates").rglob("*.md")]
    files += [p for p in (root / "docs").rglob("*") if p.is_file()]
    files += [p for p in (root / "README.md", root / "CLAUDE.md") if p.exists()]
    return sorted(files)


def dangling_refs(text: str, root: Path, source: Path | None = None) -> list[str]:
    """Framework paths and ADR numbers in text that don't exist under root. source is
    the file text came from: relative links resolve from it, and ADR numbers are only
    checked outside standards/ and templates/ (those talk about a project's own ADRs)."""
    missing = []
    base = root.resolve()
    for m in REF_RE.finditer(text):
        ref, prefix, tail = m["ref"], m["prefix"] or "", m["tail"] or ""
        if tail.startswith("?") and text[m.end() : m.end() + 1] == "=":
            tail = ""  # a URL query, not a glob
        if prefix.startswith(".."):  # a relative link: re-anchor it at the framework root
            if source is None:
                continue
            anchor = (source.parent / prefix).resolve()
            if not anchor.is_relative_to(base):
                continue  # points outside the framework
            ref = (anchor / ref).relative_to(base).as_posix()
        elif not prefix:
            # a bare templates/<x> may be the project's own (Jinja, email templates): it
            # is the framework's only when templates/<x> is one of the framework's entries
            top, _, rest = ref.partition("/")
            if (
                top == "templates"
                and rest
                and not (root / "templates" / rest.split("/")[0]).exists()
            ):
                continue
        if tail[:1] in ("*", "?", "["):  # a glob: something must match it
            pattern = (ref + tail).rstrip("./")
            # a lone trailing `?` may end a sentence instead: either reading will do
            if tail == "?" and (root / ref.rstrip("./")).exists():
                continue
            if not any(root.glob(pattern)):
                missing.append(pattern)
            continue
        if tail and "/" in ref:  # a placeholder mid-name: check its directory
            ref = ref.rsplit("/", 1)[0]
        ref = ref.rstrip("./")
        if not (root / ref).exists():
            missing.append(ref)
    rel_parts = source.resolve().relative_to(root.resolve()).parts if source else ()
    if not rel_parts or rel_parts[0] not in ("standards", "templates"):
        for m in ADR_RE.finditer(text):
            if not any((root / "decisions").glob(f"[aA][dD][rR]-{m.group(1)}-*.md")):
                missing.append(m.group(0))
    return sorted(set(missing))


def norm_pkg(name: str) -> str:
    return re.split(r"[<>=!~\[;\s]", name, maxsplit=1)[0].lower().replace("_", "-")


def pyproject_packages(root: Path) -> set[str]:
    """Every package pyproject.toml pins: dependencies, extras and dependency groups."""
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs += extra
    for group in data.get("dependency-groups", {}).values():
        specs += [s for s in group if isinstance(s, str)]
    return {norm_pkg(s) for s in specs}


def pip_args(rest: str) -> list[str]:
    """The arguments of one shell command: quotes kept together (a PEP 508 marker's `;`
    stays inside its argument), stopping at the first unquoted `;`, `&&`, `||` or `|`."""
    lexer = shlex.shlex(rest, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    args = []
    try:
        for tok in lexer:
            if tok and set(tok) <= set(";&|"):
                break
            args.append(tok)
    except ValueError:  # unbalanced quotes: take what was read
        pass
    return args


def unpinned_pip_installs(text: str, pinned: set[str]) -> list[str]:
    """Packages a `pip install` command names that the toolchain doesn't pin. Only code
    (backticks, fenced blocks, <code>/<pre>) is read: prose isn't a command."""
    found = []
    for code in CODE_RE.finditer(text):
        snippet = next(g for g in code.groups()[1:] if g is not None)
        for line in snippet.replace("\\\n", " ").splitlines():
            for m in PIP_INSTALL_RE.finditer(line):
                skip = False
                for raw in pip_args(m.group(1)):
                    tok = raw.strip("\"'()")
                    if not tok:
                        continue
                    if skip:
                        skip = False
                    elif tok in PIP_VALUE_FLAGS:
                        skip = True
                    elif (
                        tok.startswith("-")
                        or tok == "pip"
                        or not PEP508_NAME_RE.match(norm_pkg(tok))
                    ):
                        continue
                    elif norm_pkg(tok) not in pinned:
                        found.append(norm_pkg(tok))
    return found


def published_errors(meta: dict, rel: str) -> list[str]:
    """ADR-0005: `published` is mandatory on the families the published-package carve-out
    covers, so none is unclassified by omission; optional (default n/a) elsewhere."""
    value = meta.get("published")
    if value is None:
        if meta.get("family") in PUBLISHED_FAMILIES:
            return [
                (
                    f"{rel}: frontmatter missing `published` (required for "
                    f"{', '.join(sorted(PUBLISHED_FAMILIES))} standards, ADR-0005)"
                )
            ]
        return []
    if value not in TIER_VALUES:
        return [f"{rel}: published must be one of {sorted(TIER_VALUES)}"]
    return []


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
    body = text[m.end() :]

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
    elif path.parent.name != FAMILY_DIRS[fam]:
        errs.append(f"{rel}: family {fam} belongs in standards/{FAMILY_DIRS[fam]}/")
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
    errs += published_errors(meta, rel)

    stacks = meta.get("stacks")
    if stacks != "all" and not (isinstance(stacks, list) and stacks):
        errs.append(f"{rel}: stacks must be `all` or a non-empty list")
    elif isinstance(stacks, list):
        for s in stacks:
            if s not in STACK_KEYS:
                errs.append(
                    f"{rel}: unknown stack key `{s}` (allowed: {', '.join(sorted(STACK_KEYS))})"
                )
    triggers = meta.get("triggers")
    if not (isinstance(triggers, list) and triggers):
        errs.append(f"{rel}: triggers must be a non-empty list")
    else:
        for t in triggers:
            if str(t) != str(t).lower():
                errs.append(f"{rel}: trigger `{t}` must be lowercase")

    for req in meta.get("requires") or []:
        if req not in all_ids:
            errs.append(f"{rel}: requires unknown standard `{req}`")

    # Verification block
    verification = meta.get("verification") or []
    if not verification:
        errs.append(
            f"{rel}: verification must be non-empty (use a layer:A attestation "
            f"entry for advisory-only standards)"
        )
    verified_rules: set[str] = set()
    for i, v in enumerate(verification):
        if not isinstance(v, dict) or not all(k in v for k in ("cmd", "expect", "layer")):
            errs.append(f"{rel}: verification[{i}] needs cmd/expect/layer")
            continue
        if v["layer"] not in LAYERS:
            errs.append(f"{rel}: verification[{i}] layer `{v['layer']}` not in H/G/A")
        is_attest = str(v["cmd"]).startswith("attest: ")
        if is_attest != (v["layer"] == "A"):
            errs.append(
                f"{rel}: verification[{i}] — `attest: ` cmd prefix and "
                f"`layer: A` must appear together (got layer {v['layer']})"
            )
        if is_attest and len(v.get("rules") or []) != 1:
            errs.append(
                f"{rel}: verification[{i}] — attestation entries carry exactly "
                f"one rule id (got {len(v.get('rules') or [])})"
            )
        if not is_attest and bare_python_launch(str(v["cmd"])):
            errs.append(
                f"{rel}: verification[{i}] cmd runs a framework script with a bare "
                f'python — use "$GOVERNANCE_DIR/.venv/bin/python"'
            )
        if not is_attest and unsafe_xargs(str(v["cmd"])):
            errs.append(
                f"{rel}: verification[{i}] cmd pipes a file list to xargs without -0 — "
                "paths with spaces split; emit NUL-separated names and use xargs -0"
            )
        if not is_attest and hardcoded_cmd_path(str(v["cmd"])):
            errs.append(
                f"{rel}: verification[{i}] cmd hardcodes a home/absolute "
                f"path — reference framework scripts as "
                f'"$GOVERNANCE_DIR/checks/…"'
            )
        vtiers = v.get("tiers")
        if vtiers is not None and (not isinstance(vtiers, list) or not set(vtiers) <= TIER_NAMES):
            errs.append(f"{rel}: verification[{i}] tiers must be a subset of T1–T4")
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

    if hardcoded_body_path(body):
        errs.append(f"{rel}: body hardcodes a path into the governance repo — use $GOVERNANCE_DIR")
    if bare_python_launch(body):
        errs.append(
            f"{rel}: body runs a framework script with a bare python — use "
            '"$GOVERNANCE_DIR/.venv/bin/python"'
        )
    if unsafe_xargs(body):
        errs.append(
            f"{rel}: body pipes a file list to xargs without -0 — paths with spaces "
            "split; emit NUL-separated names and use xargs -0"
        )

    # Tier-line grammar + enforcement backing: every rule block carries exactly one
    # `**Tiers**: … — **Layer**: …` line; rules required at any tier need H/G
    # verification coverage or an explicit `**Layer**: A (attestation)` marker.
    blocks = RULE_HEADING_RE.split(body)  # [pre, id1, block1, id2, block2, ...]
    for rid, block in zip(blocks[1::2], blocks[2::2], strict=True):
        m_tier = TIER_LINE_RE.search(block)
        if not m_tier:
            errs.append(f"{rel}: rule {rid} missing tier line (`**Tiers**: … — **Layer**: …`)")
            continue
        tier_spec, layer_spec = m_tier.group(1), m_tier.group(2)
        if layer_spec[0] not in "HGA":
            errs.append(f"{rel}: rule {rid} layer spec must start with H, G, or A")
        if not re.fullmatch(
            r"(all|[T1-4·–/,& ]+)\s*(required|advisory|n/a)"
            r"(\s*·\s*[T1-4·–/,& ]+\s*(required|advisory|n/a))*",
            tier_spec,
        ):
            errs.append(
                f"{rel}: rule {rid} tier spec `{tier_spec}` doesn't match the "
                f"grammar (e.g. `all required`, `T1 advisory · T2–T4 required`)"
            )
        if (
            "required" in tier_spec
            and rid not in verified_rules
            and not (layer_spec.startswith("A") and "attestation" in layer_spec)
        ):
            errs.append(
                f"{rel}: required rule {rid} has no H/G verification and no "
                f"explicit `**Layer**: A (attestation)` marker"
            )

    # Sections & prose discipline
    for sec in REQUIRED_SECTIONS:
        if sec not in body:
            errs.append(f"{rel}: missing section `{sec}`")
    abstract = re.search(r"## Abstract\n+(.*?)\n## ", body, re.DOTALL)
    if abstract and len(abstract.group(1).split()) > 120:
        errs.append(f"{rel}: abstract over 120 words ({len(abstract.group(1).split())})")
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
    if not only:
        for skill in sorted((ROOT / "skills").rglob("SKILL.md")):
            skill_text = skill.read_text(encoding="utf-8")
            if bare_python_launch(skill_text):
                errors.append(
                    f"{skill.relative_to(ROOT)}: runs a framework script with a bare python "
                    "— use $GOV/.venv/bin/python"
                )
            if unsafe_xargs(skill_text):
                errors.append(
                    f"{skill.relative_to(ROOT)}: pipes a file list to xargs without -0 — "
                    "paths with spaces split; emit NUL-separated names and use xargs -0"
                )

        # Reference integrity: no stale framework path, ADR or pip package in what
        # users and agents read
        pinned = pyproject_packages(ROOT)
        for path in reference_files(ROOT):
            text = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(ROOT)
            for ref in dangling_refs(text, ROOT, path):
                errors.append(f"{rel}: names {ref}, which doesn't exist in the framework")
            if rel.parts[0] == "docs":
                for pkg in unpinned_pip_installs(text, pinned):
                    errors.append(f"{rel}: pip-installs {pkg}, which pyproject.toml doesn't pin")

    if only:
        # Partial mode: requires-resolution against not-yet-written IDs is expected
        # during parallel authoring; downgrade those to warnings.
        hard = [e for e in errors if "requires unknown standard" not in e]
        for w in (e for e in errors if e not in hard):
            print(f"  ⚠ (deferred) {w}")
        errors = hard
    else:
        # Index freshness (delegated to build-index --check)
        check = subprocess.run(  # nosec B603 - this repo's own build-index.py, no shell
            [sys.executable, str(ROOT / "checks" / "build-index.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
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
