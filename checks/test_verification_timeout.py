#!/usr/bin/env python3
"""Tests that a verification command exceeding --timeout is a FAIL row (with the whole
process group killed), not a crash that loses the report; that a detached descendant
can't stall the report; and that Ctrl-C doesn't leave the running check behind."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

VERIFY = Path(__file__).with_name("run-verification.py")

BACKGROUNDED = "sh -c 'sleep 30 & echo $! > child.pid; wait'"
# Escapes the check's process group (new session) while keeping stdout/stderr open.
DETACHED = ("python3 -c 'import subprocess; "
            "p = subprocess.Popen([\"sleep\", \"30\"], start_new_session=True); "
            "open(\"child.pid\", \"w\").write(str(p.pid))'; sleep 30")


def standard(first_cmd: str) -> str:
    return f"""---
id: TST-SLOW
version: 1.0.0
verification:
  - cmd: {json.dumps(first_cmd)}
    expect: "exit 0"
    layer: G
    rules: [TST-SLOW-01]
  - cmd: "true"
    expect: "exit 0"
    layer: G
    rules: [TST-SLOW-02]
---
"""


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_dead(pid: int, seconds: float = 5) -> bool:
    deadline = time.monotonic() + seconds
    while alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    return not alive(pid)


class TimeoutTests(unittest.TestCase):
    def setUp(self):
        self.gov = tempfile.TemporaryDirectory()
        self.proj = tempfile.TemporaryDirectory()
        self.addCleanup(self.gov.cleanup)
        self.addCleanup(self.proj.cleanup)
        (Path(self.gov.name) / "standards" / "testing").mkdir(parents=True)
        Path(self.proj.name, "GOVERNANCE.md").write_text(
            "```yaml\ntier: T1\nstandards:\n  - {id: TST-SLOW, version: 1.0.0}\n"
            "waivers: []\n```\n")
        self.pidfile = Path(self.proj.name, "child.pid")

    def use(self, first_cmd: str) -> None:
        (Path(self.gov.name) / "standards" / "testing" / "tst-slow.md").write_text(
            standard(first_cmd))

    def argv(self, timeout: int) -> list[str]:
        return [sys.executable, str(VERIFY), "--project", self.proj.name,
                "--governance-dir", self.gov.name, "--json", "--timeout", str(timeout)]

    def child_pid(self) -> int:
        pid = int(self.pidfile.read_text())
        self.addCleanup(lambda: alive(pid) and os.kill(pid, signal.SIGKILL))
        return pid

    def run_verifier(self, timeout: int = 2) -> tuple[subprocess.CompletedProcess, float]:
        start = time.monotonic()
        proc = subprocess.run(self.argv(timeout), capture_output=True, text=True,
                              check=False, timeout=60)
        return proc, time.monotonic() - start

    def assert_timeout_report(self, proc: subprocess.CompletedProcess) -> None:
        self.assertEqual(proc.returncode, 1, proc.stderr)
        checks = [r for r in json.loads(proc.stdout)["results"] if r["kind"] == "check"]
        self.assertEqual([c["status"] for c in checks], ["FAIL", "PASS"])
        self.assertIn("timed out after 2s", checks[0]["output"])

    def test_timeout_is_a_fail_row_and_kills_children(self):
        self.use(BACKGROUNDED)
        proc, elapsed = self.run_verifier()
        child = self.child_pid()
        self.assert_timeout_report(proc)
        self.assertLess(elapsed, 20)
        self.assertTrue(wait_dead(child), "backgrounded child outlived the timeout")

    def test_detached_child_holding_output_does_not_stall_report(self):
        self.use(DETACHED)
        proc, elapsed = self.run_verifier()
        self.child_pid()
        self.assert_timeout_report(proc)
        self.assertLess(elapsed, 20)

    def test_interrupt_kills_running_check(self):
        self.use(BACKGROUNDED)
        verifier = subprocess.Popen(self.argv(600), stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: verifier.poll() is None and verifier.kill())
        deadline = time.monotonic() + 10
        while not self.pidfile.exists() or not self.pidfile.read_text().strip():
            self.assertLess(time.monotonic(), deadline, "check never started")
            time.sleep(0.1)
        child = self.child_pid()
        verifier.send_signal(signal.SIGINT)
        verifier.wait(timeout=10)
        self.assertNotEqual(verifier.returncode, 0)
        self.assertTrue(wait_dead(child), "running check outlived Ctrl-C")


if __name__ == "__main__":
    unittest.main()
