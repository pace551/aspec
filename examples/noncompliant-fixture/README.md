# noncompliant-fixture

Negative-test asset for the framework itself (Phase-4 check #5): a generator for a small
Python project that violates SEC-SECRETS-01 (hardcoded key), STK-PY-03 (ruff),
STK-PY-04 (f-string SQL / bandit B608), STK-PY-02 (coverage below baseline), and
carries an expired waiver.

The violations are **generated, not stored** (`setup.sh` assembles the fake key at run
time) so this repo never contains a secret-shaped string for scanners to trip on.

```bash
# generate + verify it fails correctly
bash setup.sh /tmp/badproj --install
python3 ../../checks/run-verification.py --project /tmp/badproj   # expect FAILs citing rule IDs
```

Expected: expired-waiver FAIL, secret-scan FAIL (SEC-SECRETS-01), ruff FAIL (STK-PY-03),
bandit FAIL (STK-PY-04), ratchet FAIL (STK-PY-02). Fixing any one violation flips its
row to PASS — that flip is part of the test.
