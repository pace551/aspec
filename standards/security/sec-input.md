---
id: SEC-INPUT
title: Input Validation & Injection Defense
family: SEC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - input validation
  - sql
  - injection
  - subprocess
  - shell
  - file upload
  - path traversal
  - ssrf
  - xss
  - user input
  - pydantic
  - zod
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh"
    expect: "exit 0 — scanner catches string-built SQL and shell=True (lenient when scanner missing at T1/T2)"
    layer: G
    rules: [SEC-INPUT-02, SEC-INPUT-03]
    tiers: [T1, T2]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh --tier T3"
    expect: "exit 0 — scanner clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-INPUT-02, SEC-INPUT-03]
    tiers: [T3]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh --tier T4"
    expect: "exit 0 — scanner clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-INPUT-02, SEC-INPUT-03]
    tiers: [T4]
  - cmd: "attest: every trust boundary validates and type-coerces its input through a schema (pydantic/zod or equivalent) before use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-INPUT-01]
  - cmd: "attest: file paths derived from external input are resolved and confined to an allowlisted root"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-INPUT-04]
  - cmd: "attest: file uploads enforce size limits, content-type allowlists, and server-generated names"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-INPUT-05]
    tiers: [T3, T4]
  - cmd: "attest: URL-fetching features validate scheme and host and block private/metadata address ranges (SSRF)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-INPUT-06]
    tiers: [T3, T4]
  - cmd: "attest: untrusted data reaches HTML only through framework auto-escaping; no innerHTML/dangerouslySetInnerHTML with external data"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-INPUT-07]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Input Validation & Injection Defense (SEC-INPUT)

## Abstract

Every injection class is the same bug: external data crossing a trust boundary and being
interpreted as code — SQL, shell, path, HTML, or URL. The defense is uniform: validate
and type-coerce at the edge (pydantic/zod), then use APIs that keep data and code
structurally separate — parameterized queries, `subprocess` argument lists, resolved and
confined paths, framework auto-escaping, allowlisted fetch targets. The two
machine-checkable rules (SQL, shell) are gated through `checks/sec-sast.sh`; the rest are
attested. Required from T2 up — research pipelines parse untrusted external data too;
web-specific delivery hardening layers on top in SEC-WEB.

## Normative Rules

### SEC-INPUT-01 — External input MUST be validated and type-coerced at every trust boundary

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

At the edge — HTTP handler, CLI arg parsing, file/queue ingestion, LLM output parsing —
input passes through a schema (pydantic v2 in Python, zod in TypeScript, per the stack
standards) that types, bounds, and rejects before any business logic runs. Inside the
boundary, code handles typed values, never raw dicts/strings. Validation is
allowlist-shaped ("a ticker is `^[A-Z]{1,5}$`"), not blocklist-shaped ("strip the bad
characters"). LLM responses and third-party API payloads are external input — parse
them through the same schemas.

### SEC-INPUT-02 — SQL MUST be parameterized; building queries from strings is prohibited

**Tiers**: all required — **Layer**: G

The canonical anti-pattern is `f"SELECT … WHERE user = '{name}'"` — f-string, `%`,
`.format()`, or `+` concatenation of any external value into SQL, at any tier (bandit
B608 fires everywhere, matching STK-PY-04). Use driver placeholders
(`execute("… WHERE user = ?", (name,))`) or the ORM's expression layer. Identifiers
(table/column names) can't be parameterized — when dynamic, they come from a hardcoded
allowlist mapping, never from input. The same rule covers NoSQL: no string-built query
documents or `$where` JavaScript.

### SEC-INPUT-03 — Subprocesses MUST use argument lists; `shell=True` with interpolated input is prohibited

**Tiers**: all required — **Layer**: G

`subprocess.run([...], shell=False)` with an argv list (bandit B602/B604 gate this);
`execFile`/`spawn` over `exec` in Node. If a shell feature (pipe, glob) is genuinely
needed, the command string is a constant and external values arrive as arguments or
env vars — never interpolated into the string. Filenames are still attack input:
a file named `--delete-all` argues for `--` end-of-options markers and absolute paths.

### SEC-INPUT-04 — File paths derived from input MUST be resolved and confined to an allowlisted root

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

`../` traversal survives naive prefix checks and URL-encoding tricks. The pattern:
resolve first, then verify containment —
`p = (ROOT / name).resolve(); p.is_relative_to(ROOT.resolve())` — and reject on
failure. Serving files goes through the framework's static handler (which does this)
rather than hand-built `open(base + name)`. Archive extraction is the same bug wearing
a coat (zip-slip): validate each member's resolved destination before writing.

### SEC-INPUT-05 — File uploads MUST enforce size, type, and name discipline

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Three limits, all server-side: a byte-size cap enforced during streaming (not after
buffering the whole body); a content-type allowlist verified against file content
(magic bytes) rather than the client's claimed `Content-Type` or extension; and
server-generated storage names (UUIDs) with the original filename kept only as
sanitized metadata. Uploads land outside any web-served or code path — object storage
or a dedicated directory — so an uploaded `.html` or `.py` is inert data, never
something the origin executes or serves inline.

### SEC-INPUT-06 — URL-fetching features MUST validate targets and block internal address ranges

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Any feature that fetches a URL influenced by input — webhooks, "import from URL", link
previews, RSS — is an SSRF vector: the server can be steered at
`http://169.254.169.254/` (cloud metadata → credentials) or internal services that
trust the network. Require `https?` schemes, allowlist hosts where the feature permits
it, resolve the hostname and reject private/link-local/loopback ranges, and re-check on
redirects (a public URL that 302s to the metadata IP is the classic bypass). Fetch with
timeouts and response-size caps per the httpx conventions in STK-PY-07.

### SEC-INPUT-07 — Untrusted data MUST reach HTML only through escaping

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

XSS is injection into the DOM. Stay inside the framework's auto-escaping (JSX text,
Jinja2 autoescape) and treat its escape hatches — `dangerouslySetInnerHTML`,
`innerHTML`/`document.write`, Jinja's `| safe` — as prohibited for external data;
rendering sanitized rich text requires DOMPurify or equivalent, named in code review.
LLM-generated content shown to users is untrusted data. This rule is the payload-side
XSS defense; SEC-WEB-01's CSP is the second layer that catches what slips through.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/sec-sast.sh` (T1/T2) | exit 0 — no B608/B602-class findings | SEC-INPUT-02, -03 |
| 2 | `… sec-sast.sh --tier T3` (T3) | exit 0; missing scanner fails | SEC-INPUT-02, -03 |
| 3 | `… sec-sast.sh --tier T4` (T4) | exit 0; missing scanner fails | SEC-INPUT-02, -03 |
| 4 | attest: schema validation at every boundary | explicit yes recorded | SEC-INPUT-01 |
| 5 | attest: paths resolved + confined | explicit yes recorded | SEC-INPUT-04 |
| 6 | attest: upload size/type/name limits (T3+) | explicit yes recorded | SEC-INPUT-05 |
| 7 | attest: SSRF target validation (T3+) | explicit yes recorded | SEC-INPUT-06 |
| 8 | attest: HTML only via escaping (T3+) | explicit yes recorded | SEC-INPUT-07 |

**Remediation:** B608 → rewrite with placeholders; dynamic identifiers → allowlist map ·
B602 → argv list, `shell=False`; constant string + args if shell features are required ·
traversal → resolve-then-`is_relative_to` helper, reuse it everywhere · SSRF → central
`fetch_external(url)` wrapper owning scheme/host/IP/redirect checks · XSS → delete the
escape hatch; if rich text is a requirement, sanitize with DOMPurify and say so in the PR.

## Worked Example

The four highest-frequency defenses in one edge handler:

```python
from pathlib import Path
import subprocess
from pydantic import BaseModel, Field

REPORTS_ROOT = Path("/srv/reports").resolve()

class ReportRequest(BaseModel):                      # SEC-INPUT-01: typed edge
    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")     # allowlist, not blocklist
    year: int = Field(ge=1993, le=2100)

def build_report(req: ReportRequest, db) -> Path:
    rows = db.execute(                               # SEC-INPUT-02: placeholders
        "SELECT * FROM filings WHERE ticker = ? AND year = ?",
        (req.ticker, req.year),
    ).fetchall()

    out = (REPORTS_ROOT / f"{req.ticker}-{req.year}.pdf").resolve()
    if not out.is_relative_to(REPORTS_ROOT):         # SEC-INPUT-04: confine
        raise ValueError("path escapes report root")

    subprocess.run(                                  # SEC-INPUT-03: argv list
        ["wkhtmltopdf", "--quiet", "-", str(out)],
        input=render(rows), check=True, timeout=60,
    )
    return out
```

Every external value is typed before use, and no string it contains is ever
interpreted as SQL, shell, or path structure.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `f"SELECT … '{user_input}'"` | The canonical injection; bandit B608 | Placeholders / ORM expressions (SEC-INPUT-02) |
| "We escape quotes before building the SQL" | Blocklist sanitizing loses to encodings and second-order data | Parameterize; never build (SEC-INPUT-02) |
| `subprocess.run(cmd_string, shell=True)` | Filename `; rm -rf ~` is a valid filename | argv list, `shell=False` (SEC-INPUT-03) |
| `open(UPLOAD_DIR + filename)` | `../../../etc/passwd` traversal | resolve + `is_relative_to` (SEC-INPUT-04) |
| Trusting client `Content-Type` / extension | Attacker-controlled header; polyglot files | Magic-byte check + server names (SEC-INPUT-05) |
| Fetching any URL a user submits | SSRF into 169.254.169.254 → cloud credentials | Scheme/host/IP validation + redirect re-check (SEC-INPUT-06) |
| `dangerouslySetInnerHTML={{__html: comment}}` | Stored XSS; combined with localStorage tokens, account takeover | Auto-escaped rendering; DOMPurify for rich text (SEC-INPUT-07) |
| Validating deep in business logic, differently per call site | Boundaries drift; one forgotten site is enough | One schema at the edge (SEC-INPUT-01) |

## References

- OWASP Injection Prevention & SQL Injection Prevention Cheat Sheets — the
  parameterize-don't-sanitize doctrine of SEC-INPUT-02.
- OWASP Path Traversal & File Upload Cheat Sheets — resolve-then-contain and
  magic-byte/size/name guidance for SEC-INPUT-04/-05.
- OWASP SSRF Prevention Cheat Sheet — allowlist + private-range blocking and the
  redirect bypass covered in SEC-INPUT-06.
- OWASP XSS Prevention Cheat Sheet — context-aware escaping model behind SEC-INPUT-07.
- Capital One 2019 breach post-mortems — SSRF → metadata credentials, the concrete
  scenario SEC-INPUT-06 exists to prevent.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
