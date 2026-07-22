---
id: SEC-CRYPTO
title: Cryptography & Transport
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
  - encryption
  - tls
  - https
  - hashing
  - md5
  - sha
  - crypto
  - certificate
  - random token
  - at rest
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh"
    expect: "exit 0 — scanner flags MD5/SHA1-for-security and insecure modes (lenient when scanner missing at T1/T2)"
    layer: G
    rules: [SEC-CRYPTO-02]
    tiers: [T1, T2]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh --tier T3"
    expect: "exit 0 — scanner clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-CRYPTO-02]
    tiers: [T3]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh --tier T4"
    expect: "exit 0 — scanner clean; missing scanner FAILS at this tier"
    layer: G
    rules: [SEC-CRYPTO-02]
    tiers: [T4]
  - cmd: "attest: no cryptographic primitive was hand-rolled; all crypto goes through vetted libraries at their safe defaults"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-CRYPTO-01]
  - cmd: "attest: all traffic rides TLS — including service-to-service and internal hops at T3+; no plaintext http beyond localhost"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-CRYPTO-03]
    tiers: [T3, T4]
  - cmd: "attest: new cryptographic choices came from the standard-choices table (or the deviation is documented with a reason)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-CRYPTO-04]
  - cmd: "attest: key material is stored, scoped, and rotated per SEC-SECRETS; no keys are hardcoded or derived from passwords ad hoc"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-CRYPTO-05]
last_review: 2026-07-22
---

# Cryptography & Transport (SEC-CRYPTO)

## Abstract

Crypto fails quietly: the wrong primitive encrypts and decrypts convincingly for years
while providing nothing. So the rules are choices, not implementations: never hand-roll a
primitive; take the answer from the standard-choices table (SHA-256+ for integrity,
argon2id for passwords, `secrets.token_urlsafe` for tokens, AES-GCM via a vetted library,
SQLCipher or cloud-managed encryption at rest); prohibit the deprecated set (MD5/SHA-1
for security, ECB mode, TLS <1.2) — machine-checked via `checks/sec-sast.sh`; run TLS
everywhere, including internal hops at T3+; and manage key material per SEC-SECRETS. If a
task involves inventing a scheme, the task is wrong.

## Normative Rules

### SEC-CRYPTO-01 — Cryptographic primitives MUST NOT be hand-rolled

**Tiers**: all required — **Layer**: A (attestation)

No custom ciphers, hash constructions, MACs, padding, token formats, or "obfuscation"
layers (XOR with a repeated key is the classic). Use vetted libraries at their safe
defaults: `cryptography` (Fernet for the common encrypt-a-blob case), libsodium/PyNaCl,
the platform TLS stack, `hashlib`/`secrets` from the stdlib. Composing primitives
(manual CBC + your own padding + your own MAC ordering) counts as hand-rolling — the
famous failures live in the composition. If the table in SEC-CRYPTO-04 lacks a row for
the need, the move is to add a row deliberately, not to improvise inline.

### SEC-CRYPTO-02 — Deprecated primitives MUST NOT be used for security purposes

**Tiers**: all required — **Layer**: G

Prohibited where security is the purpose: MD5 and SHA-1 (collisions are practical),
DES/3DES/RC4, ECB mode for any cipher (identical plaintext blocks produce identical
ciphertext — the penguin picture), `random`/`Math.random` for anything secret, and
TLS 1.0/1.1. Scanners gate the common cases (bandit B324 weak hashes, B304/B305 insecure
ciphers/modes, B311 pseudo-random for security). Non-security uses of fast hashes
(cache keys, dedup, sharding) are legitimate — mark them explicitly
(`hashlib.md5(data, usedforsecurity=False)`) so the scanner and the reader both know.

### SEC-CRYPTO-03 — TLS everywhere; internal traffic included at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every external call is `https://` (or wss/smtps equivalents) — no plaintext beyond
`localhost`. At T3+ the same applies to internal hops: service-to-service, app-to-
database (`sslmode=require` at minimum for Postgres), and anything crossing a cloud
network — "internal" networks are a trust boundary other tenants and one misconfig
share. TLS 1.2 floor, 1.3 preferred; certificates come from ACM or Let's Encrypt with
auto-renewal (a manually renewed cert is an outage on a timer). Certificate
verification is never disabled — `verify=False` "temporarily" is the anti-pattern that
outlives its author; a local-CA bundle is the fix for internal certs.

### SEC-CRYPTO-04 — Cryptographic choices SHOULD come from the standard-choices table

**Tiers**: all advisory — **Layer**: A (attestation)

| Need | Use | Never |
|---|---|---|
| Password verifiers | argon2id (bcrypt acceptable) — SEC-AUTHN-02 | MD5/SHA-anything, reversible storage |
| Integrity / content hash | SHA-256, SHA-512, or BLAKE2 | MD5, SHA-1 |
| Random tokens / ids | `secrets.token_urlsafe(32)` / `crypto.randomBytes(32)` | `random.random()`, `Math.random()`, timestamps, UUIDv1 |
| Symmetric encryption | AES-256-GCM or ChaCha20-Poly1305 (Fernet as the easy default) | ECB mode, CBC without a MAC, homemade schemes |
| Key derivation from passwords | argon2id or PBKDF2-HMAC-SHA256 (≥600k iters) | A single hash round as a "key" |
| Signatures / verification | Ed25519; HMAC-SHA256 for shared-secret (webhooks) | RSA-1024, DSA, truncated MACs |
| At rest (local) | SQLCipher for SQLite; OS FileVault as baseline | DIY file encryption |
| At rest (cloud) | S3 SSE-KMS, RDS/EBS/DynamoDB encryption switched on | Client-side schemes invented per-project |
| In transit | TLS 1.2+ (1.3 preferred) — SEC-CRYPTO-03 | TLS 1.0/1.1, plaintext, `verify=False` |

Deviation is permitted with a written reason (that's SHOULD) — the table exists so the
decision is made once, here, not re-derived from training data per session (C8: check
current guidance when adding rows).

### SEC-CRYPTO-05 — Key material MUST be managed per SEC-SECRETS

**Tiers**: all required — **Layer**: A (attestation)

Encryption keys, signing keys, and webhook secrets are secrets: stored on the
SEC-SECRETS tier ladder (`.env` → Keychain → SSM/KMS), never hardcoded, never derived
ad hoc from a password sitting in config. Prefer KMS-managed keys at T3+ so rotation
and audit come free with the envelope. Plan for rotation at generation time — version
your ciphertext or token format (Fernet's `MultiFernet` exists for exactly this) so
re-keying is an operation, not a migration crisis. A compromised key follows
SEC-SECRETS-05: rotate first, clean up second.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/sec-sast.sh` (T1/T2) | exit 0 — no weak-hash/insecure-mode findings | SEC-CRYPTO-02 |
| 2 | `… sec-sast.sh --tier T3` (T3) | exit 0; missing scanner fails | SEC-CRYPTO-02 |
| 3 | `… sec-sast.sh --tier T4` (T4) | exit 0; missing scanner fails | SEC-CRYPTO-02 |
| 4 | attest: no hand-rolled primitives | explicit yes recorded | SEC-CRYPTO-01 |
| 5 | attest: TLS everywhere incl. internal at T3+ | explicit yes recorded | SEC-CRYPTO-03 |
| 6 | attest: choices from the table or documented deviation | explicit yes recorded | SEC-CRYPTO-04 |
| 7 | attest: keys managed per SEC-SECRETS | explicit yes recorded | SEC-CRYPTO-05 |

**Remediation:** B324 on a cache key → `usedforsecurity=False` and move on; on anything
security-relevant → SHA-256 · `random` for a token → `secrets.token_urlsafe` ·
`verify=False` → fix the CA bundle (`certifi`, or the internal CA cert), never ship the
bypass · hand-rolled encrypt function → replace with Fernet; treat existing ciphertext
as a migration, not a reason to keep the scheme.

## Worked Example

The common cases, done from the table:

```python
import secrets
from cryptography.fernet import Fernet, MultiFernet

# Random token for a session/reset link (SEC-CRYPTO-04 row 3)
token = secrets.token_urlsafe(32)

# Encrypt-a-blob with rotation headroom (SEC-CRYPTO-01/-05)
# key from SSM/Keychain per SEC-SECRETS — generated once with Fernet.generate_key()
f = MultiFernet([Fernet(current_key), Fernet(previous_key)])
ciphertext = f.encrypt(b"statement pdf bytes")
plaintext = f.decrypt(ciphertext)          # tries current, falls back to previous

# Integrity hash for dedup — fast hash, explicitly non-security
import hashlib
digest = hashlib.sha256(file_bytes).hexdigest()
```

Postgres connection string honoring SEC-CRYPTO-03 at T3:
`postgresql://app@db.internal:5432/myapp?sslmode=require`. At-rest for the same tier:
RDS encryption enabled at creation (it cannot be toggled on later without a snapshot
restore — choose correctly on day one).

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| XOR/base64 "encryption" for stored data | Obfuscation, zero confidentiality; reversible by inspection | Fernet/AES-GCM from the table (SEC-CRYPTO-01) |
| `hashlib.md5(password)` — even salted | GPU-crackable by design | argon2id (SEC-AUTHN-02) |
| AES-ECB because it "just works" | Structure leaks through identical blocks | AES-GCM / ChaCha20-Poly1305 (SEC-CRYPTO-02) |
| `random.random()` for tokens or ids | Mersenne Twister is predictable from outputs | `secrets` module (SEC-CRYPTO-04) |
| `requests.get(url, verify=False)` | Disables the only authentication TLS provides; lives forever | Fix the CA bundle (SEC-CRYPTO-03) |
| Manually renewed certificates | An outage scheduled for the week everyone forgot | ACM / Let's Encrypt auto-renewal |
| Encryption key hardcoded next to the ciphertext | Lock taped to its key; also a SEC-SECRETS-01 breach | Key on the SEC-SECRETS ladder (SEC-CRYPTO-05) |
| Inventing a token format with truncated HMACs | Composition bugs (length extension, timing) are the norm | Fernet or full HMAC-SHA256 via `hmac.compare_digest` |

## References

- OWASP Cryptographic Storage Cheat Sheet — algorithm selections behind the
  SEC-CRYPTO-04 table.
- OWASP Transport Layer Security Cheat Sheet — TLS 1.2 floor and internal-traffic
  posture of SEC-CRYPTO-03.
- Python `cryptography` docs (Fernet/MultiFernet) — the sanctioned easy path for
  symmetric encryption and key rotation.
- NIST SP 800-131A — the formal deprecation schedule behind SEC-CRYPTO-02's banned
  list.
- SQLCipher documentation — the local-SQLite at-rest row of the table.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
