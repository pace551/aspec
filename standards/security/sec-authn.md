---
id: SEC-AUTHN
title: Authentication
family: SEC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - login
  - authentication
  - password
  - session
  - jwt
  - oauth
  - mfa
  - signup
  - sso
  - cognito
requires: []
verification:
  - cmd: "attest: user-facing auth is delegated to a managed identity provider, or the hand-rolled exception is documented with a reason"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHN-01]
    tiers: [T3, T4]
  - cmd: "attest: any stored password verifiers use argon2id or bcrypt — no MD5/SHA-family, no reversible storage, anywhere, ever"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHN-02]
  - cmd: "attest: sessions ride httpOnly/Secure/SameSite cookies; no auth tokens are kept in localStorage or sessionStorage"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHN-03]
    tiers: [T3, T4]
  - cmd: "attest: MFA is enabled on James's AWS and GitHub accounts, and (at T4) on every admin and cloud account touching this project"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHN-04]
  - cmd: "attest: login, signup, and password-reset endpoints are throttled against brute force"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-AUTHN-05]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Authentication (SEC-AUTHN)

## Abstract

Who is this? Answered wrong, every other control is decoration. The house position: don't
build authentication — buy the free tier. At T3+ user-facing auth is delegated to a
managed provider (Cognito, Auth0, Clerk, or plain OAuth "sign in with GitHub/Google");
hand-rolling is the documented exception. Where passwords are unavoidable they are hashed
with argon2id or bcrypt — never MD5/SHA — sessions live in httpOnly/Secure/SameSite
cookies rather than localStorage JWTs, auth endpoints are throttled, and MFA covers all
admin and cloud accounts at T4. James's own AWS and GitHub MFA is constitution-adjacent:
always on, regardless of any project's tier.

## Normative Rules

### SEC-AUTHN-01 — T3+ user-facing auth MUST use a managed identity provider, not hand-rolled credentials

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Cognito, Auth0, Clerk, or OAuth/OIDC delegation to GitHub/Google — all have free tiers
that outlast a solo product's early life (C6-compatible). The provider owns password
storage, reset flows, breach detection, and MFA UX: exactly the code that is maximally
dangerous to write and zero differentiation to own. Hand-rolling is the exception and
needs a documented reason in `GOVERNANCE.md` — at which point SEC-AUTHN-02/-03/-05
stop being backstops and become your load-bearing walls. Machine-to-machine credentials
(API keys, service tokens) are SEC-SECRETS territory, not this rule's.

### SEC-AUTHN-02 — Stored passwords MUST be hashed with argon2id or bcrypt; MD5/SHA-family for passwords is prohibited everywhere, always

**Tiers**: all required — **Layer**: A (attestation)

argon2id (first choice) or bcrypt (acceptable; mind its 72-byte input truncation) —
both salted and deliberately slow. General-purpose hashes (MD5, SHA-1, SHA-256, even
salted) are GPU-fast by design and fall to offline cracking; they are banned for
passwords at every tier including throwaway T1 scripts, because throwaway credential
handling has a way of getting reused. Never store reversible (encrypted or plaintext)
passwords. Policy follows NIST 800-63B: length over composition rules, no periodic
forced rotation, verify with a constant-time comparison via the library — never
`hash == candidate` string equality.

### SEC-AUTHN-03 — Sessions MUST ride httpOnly/Secure/SameSite cookies; tokens MUST NOT live in localStorage

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`httpOnly` puts the session token beyond the reach of any injected script — one XSS no
longer equals full account takeover, which is precisely why localStorage/sessionStorage
JWTs are prohibited: they are readable by every script on the page. `Secure` keeps the
cookie off plaintext HTTP; `SameSite=Lax` (or `Strict`) is the CSRF floor. Sessions
expire server-side, and logout actually invalidates — a "stateless" JWT that cannot be
revoked before expiry is a design smell, not a feature. Exact flag reference and header
context live in SEC-WEB-04.

### SEC-AUTHN-04 — MFA MUST be enabled on James's AWS and GitHub always, and on all admin/cloud accounts at T4

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

Constitution-adjacent: the personal AWS root/IAM and GitHub accounts are the keys to
every project at every tier, so their MFA is unconditional house policy — the tier line
above scopes only the *project-wide sweep*. At T4 every account that can administer the
product or its infrastructure (cloud console, registrar, email provider, payment
dashboard, CI org) has MFA — TOTP or hardware key, not SMS where avoidable. If the
product has an admin login, offer MFA to those users too.

### SEC-AUTHN-05 — Login, signup, and reset endpoints MUST be throttled against brute force

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Per-account and per-IP rate limits with backoff or lockout-with-cooldown on login,
signup, and password-reset — the three endpoints attackers script first (credential
stuffing runs at machine speed against anything public). Failure responses stay
uniform: same message and comparable timing for "no such user" and "wrong password", so
the endpoint doesn't double as a username oracle. A managed provider (SEC-AUTHN-01)
gives this for free; hand-rolled auth implements it via the rate-limiting machinery of
SEC-WEB-03.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: managed provider or documented exception (T3+) | explicit yes recorded | SEC-AUTHN-01 |
| 2 | attest: argon2id/bcrypt only, never MD5/SHA | explicit yes recorded | SEC-AUTHN-02 |
| 3 | attest: httpOnly/Secure/SameSite cookies, no localStorage tokens (T3+) | explicit yes recorded | SEC-AUTHN-03 |
| 4 | attest: MFA on personal AWS/GitHub always; all admin/cloud accounts at T4 | explicit yes recorded | SEC-AUTHN-04 |
| 5 | attest: auth endpoints throttled (T3+) | explicit yes recorded | SEC-AUTHN-05 |

**Remediation:** hand-rolled auth found at T3+ → migrate to a provider or record the
waiver-with-reason now · legacy MD5/SHA verifiers → rehash each user's password with
argon2id at next successful login, force-reset stragglers · JWT in localStorage → move
to an httpOnly cookie; if a SPA "needs" JS-readable tokens, put the API behind the same
origin · MFA gap → enable today; it is a settings page, not a project.

## Worked Example

Passwords done correctly (the unavoidable-password case):

```python
from argon2 import PasswordHasher, exceptions

ph = PasswordHasher()                      # argon2id, library defaults
stored = ph.hash("correct horse battery staple")

def login(stored: str, candidate: str) -> bool:
    try:
        ph.verify(stored, candidate)       # constant-time inside the library
        return True
    except exceptions.VerifyMismatchError:
        return False
```

Session cookie set the SEC-AUTHN-03 way (FastAPI):

```python
import secrets

token = secrets.token_urlsafe(32)          # server-side session id (SEC-CRYPTO table)
response.set_cookie(
    "session", token,
    httponly=True, secure=True, samesite="lax",
    max_age=8 * 3600,
)
```

At T3, prefer deleting both snippets and letting Clerk/Cognito own the flow
(SEC-AUTHN-01) — the best auth code is the auth code you don't maintain.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Hand-rolled login for a weekend product | You now own breach detection, resets, and cracking economics | Managed provider free tier (SEC-AUTHN-01) |
| `sha256(password + salt)` | GPU-fast by design; cracked at billions/sec offline | argon2id/bcrypt (SEC-AUTHN-02) |
| JWT in localStorage "for the SPA" | Readable by any injected script; XSS = account takeover | httpOnly cookie (SEC-AUTHN-03) |
| Non-revocable stateless JWT sessions | Logout and compromise response both become "wait for expiry" | Server-side session or short-TTL + revocation list |
| "User not found" vs "wrong password" messages | Free username enumeration oracle | Uniform failure response (SEC-AUTHN-05) |
| MFA postponed as a launch-week task | The window between launch and MFA is when stuffing hits | It's a settings page — enable it now (SEC-AUTHN-04) |
| `hash == candidate` string comparison | Timing side-channel | The library's verify function |

## References

- OWASP Password Storage Cheat Sheet — argon2id-first ranking and bcrypt's 72-byte
  caveat, transcribed into SEC-AUTHN-02.
- NIST SP 800-63B — the modern password policy (length over composition, no forced
  rotation) SEC-AUTHN-02 adopts.
- OWASP Session Management Cheat Sheet — cookie-flag and server-side-expiry guidance
  behind SEC-AUTHN-03.
- OWASP Credential Stuffing Prevention Cheat Sheet — the throttling patterns of
  SEC-AUTHN-05.
- AWS IAM best practices — MFA-on-root guidance making SEC-AUTHN-04 house policy, not
  opinion.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
