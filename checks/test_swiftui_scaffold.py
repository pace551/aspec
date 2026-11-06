#!/usr/bin/env python3
"""Tests for the swiftui scaffold's scripts that CI runs (templates/ci/swiftui.yml).

license-audit.py backs LEG-LICENSING-01 for SwiftPM: no tool reports SwiftPM licenses
(deps.dev, behind osv-scanner --licenses, has no SwiftPM data), so every pin in
Package.resolved needs a reviewed line in licenses.allow naming an allowed license.
The worked example's scripts must match the scaffold's, since ASPEC's own
swiftui-template workflow runs them on the example.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = ROOT / "templates" / "scaffolds" / "swiftui"
EXAMPLE = ROOT / "examples" / "swiftui"
AUDIT = SCAFFOLD / "scripts" / "license-audit.py"
SRC = "https://github.com/example"  # where resolved_v3/resolved_v1 say pins come from
MANIFEST_WITH_DEPENDENCY = (
    'let package = Package(dependencies: [.package(url: "https://x/y.git", from: "1.0.0")])\n'
)


def resolved_v3(*identities: str) -> str:
    pins = [
        {
            "identity": name,
            "kind": "remoteSourceControl",
            "location": f"{SRC}/{name}.git",
            "state": {"revision": "0" * 40, "version": "1.0.0"},
        }
        for name in identities
    ]
    return json.dumps({"originHash": "x", "pins": pins, "version": 3})


def resolved_v1(*names: str) -> str:
    pins = [
        {
            "package": name,
            "repositoryURL": f"{SRC}/{name.lower()}.git",
            "state": {"branch": None, "revision": "0" * 40, "version": "1.0.0"},
        }
        for name in names
    ]
    return json.dumps({"object": {"pins": pins}, "version": 1})


class LicenseAuditTests(unittest.TestCase):
    def audit(self, files: dict[str, str]) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                path = Path(tmp, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(text, bytes):
                    path.write_bytes(text)
                else:
                    path.write_text(text)
            return subprocess.run(
                [sys.executable, str(AUDIT)], cwd=tmp, capture_output=True, text=True, check=False
            )

    def assert_exit(self, files: dict[str, str], code: int, needle: str = "") -> None:
        r = self.audit(files)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        self.assertIn(needle, r.stdout + r.stderr)

    def test_no_dependencies_passes(self):
        self.assert_exit({}, 0, "no Package.resolved")

    def test_every_pin_reviewed_and_allowed_passes(self):
        self.assert_exit(
            {
                "Package.resolved": resolved_v3("swift-collections", "swift-log"),
                "licenses.allow": (
                    f"# reviewed\n{SRC}/swift-collections 1.0.0 Apache-2.0\n"
                    f"{SRC}/swift-log 1.0.0 Apache-2.0\n"
                ),
            },
            0,
        )

    def test_unreviewed_pin_fails(self):
        self.assert_exit(
            {
                "Package.resolved": resolved_v3("swift-collections", "swift-log"),
                "licenses.allow": f"{SRC}/swift-collections 1.0.0 Apache-2.0\n",
            },
            1,
            "github.com/example/swift-log 1.0.0: no reviewed license",
        )

    def test_disallowed_license_fails(self):
        self.assert_exit(
            {
                "Package.resolved": resolved_v3("gpl-kit"),
                "licenses.allow": f"{SRC}/gpl-kit 1.0.0 GPL-3.0-only\n",
            },
            1,
            "github.com/example/gpl-kit 1.0.0: GPL-3.0-only is not on the allowlist",
        )

    def test_dependencies_without_a_review_file_fail(self):
        self.assert_exit({"Package.resolved": resolved_v3("swift-log")}, 1, "licenses.allow")

    def test_version_1_lockfile_is_read(self):
        self.assert_exit(
            {
                "Package.resolved": resolved_v1("Alamofire"),
                "licenses.allow": f"{SRC}/alamofire 1.0.0 MIT\n",
            },
            0,
        )
        self.assert_exit({"Package.resolved": resolved_v1("Alamofire")}, 1, "alamofire")

    def test_unparseable_lockfile_is_an_error(self):
        self.assert_exit({"Package.resolved": "{not json"}, 2, "Package.resolved")

    def test_a_version_change_needs_a_new_review(self):
        self.assert_exit(
            {
                "Package.resolved": resolved_v3("swift-log"),
                "licenses.allow": f"{SRC}/swift-log 0.9.0 Apache-2.0\n",
            },
            1,
            "github.com/example/swift-log 1.0.0: no reviewed license",
        )

    def test_xcode_project_lockfile_is_audited(self):
        lock = "App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        self.assert_exit({lock: resolved_v3("swift-log")}, 1, "swift-log")
        self.assert_exit(
            {
                lock: resolved_v3("swift-log"),
                "licenses.allow": f"{SRC}/swift-log 1.0.0 MIT\n",
            },
            0,
        )

    def test_non_object_lockfile_is_an_error(self):
        self.assert_exit({"Package.resolved": "[]"}, 2, "Package.resolved")

    def test_non_utf8_review_file_is_an_error(self):
        self.assert_exit(
            {"Package.resolved": resolved_v3("swift-log"), "licenses.allow": b"caf\xe9 1 MIT\n"},
            2,
            "licenses.allow",
        )

    def test_a_fork_at_the_same_version_needs_its_own_review(self):
        forked = resolved_v3("swift-log").replace("github.com/example/", "github.com/fork/")
        self.assert_exit(
            {
                "Package.resolved": forked,
                "licenses.allow": f"{SRC}/swift-log 1.0.0 MIT\n",
            },
            1,
            "github.com/fork/swift-log 1.0.0: no reviewed license",
        )

    def test_location_spellings_match(self):
        # scheme/host case, a .git suffix and a trailing slash don't make a different source
        self.assert_exit(
            {
                "Package.resolved": resolved_v3("swift-log"),
                "licenses.allow": "HTTPS://GitHub.COM/example/swift-log.git/ 1.0.0 MIT\n",
            },
            0,
        )

    def test_path_case_is_a_different_source(self):
        # repository paths are case-sensitive on many git hosts
        self.assert_exit(
            {
                "Package.resolved": resolved_v3("swift-log"),
                "licenses.allow": f"{SRC}/Swift-Log 1.0.0 MIT\n",
            },
            1,
            "no reviewed license",
        )

    def test_malformed_review_line_is_an_error(self):
        self.assert_exit(
            {"Package.resolved": resolved_v3("swift-log"), "licenses.allow": "swift-log\n"},
            2,
            "licenses.allow:1",
        )


SCA = SCAFFOLD / "scripts" / "sca.sh"
STUB = '#!/bin/sh\necho "$@" >> "$OSV_CALLS"\nexit "${OSV_EXIT:-0}"\n'


class ScaTests(unittest.TestCase):
    """scripts/sca.sh runs osv-scanner on every SwiftPM lockfile, and fails when the
    manifest declares dependencies but no lockfile is committed."""

    def sca(
        self, files: dict[str, str], osv_exit: int = 0
    ) -> tuple[subprocess.CompletedProcess, str]:
        with tempfile.TemporaryDirectory() as tmp:
            proj, bindir = Path(tmp, "proj"), Path(tmp, "bin")
            (proj / "scripts").mkdir(parents=True)
            bindir.mkdir()
            shutil.copy(SCA, proj / "scripts" / "sca.sh")
            for name, text in files.items():
                (proj / name).parent.mkdir(parents=True, exist_ok=True)
                (proj / name).write_text(text)
            stub = bindir / "osv-scanner"
            stub.write_text(STUB)
            stub.chmod(0o755)
            calls = Path(tmp, "calls")
            env = {
                "PATH": f"{bindir}:/usr/bin:/bin",
                "OSV_CALLS": str(calls),
                "OSV_EXIT": str(osv_exit),
            }
            r = subprocess.run(
                ["bash", "scripts/sca.sh"],
                cwd=proj,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            return r, calls.read_text() if calls.exists() else ""

    def test_no_dependencies_passes_without_scanning(self):
        r, calls = self.sca({"Package.swift": 'let package = Package(name: "x")\n'})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(calls, "")

    def test_every_lockfile_is_scanned(self):
        xcode = "My App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        r, calls = self.sca({"Package.resolved": "{}", xcode: "{}"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--lockfile ./Package.resolved", calls)
        self.assertIn(f"--lockfile ./{xcode}", calls)

    def test_findings_fail(self):
        r, _ = self.sca({"Package.resolved": "{}"}, osv_exit=1)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


LOCKCHECK = SCAFFOLD / "scripts" / "lockfile-check.py"
# A fake `swift`: `package resolve` writes $RESOLVED (if set) as Package.resolved, as
# SwiftPM would; with $RESOLVED unset it writes nothing (no remote dependencies).
SWIFT_STUB = """#!/bin/sh
if [ "$2" = resolve ]; then [ -n "$RESOLVED" ] && cp "$RESOLVED" Package.resolved; exit 0; fi
exit 2
"""
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


class LockfileCheckTests(unittest.TestCase):
    """scripts/lockfile-check.py: whatever `swift package resolve` pins must match the
    Package.resolved committed to git (so transitive remote dependencies count too)."""

    def check(self, committed=None, resolved=None, worktree=None, track=True, repo=True):
        with tempfile.TemporaryDirectory() as tmp:
            proj, bindir = Path(tmp, "proj"), Path(tmp, "bin")
            (proj / "scripts").mkdir(parents=True)
            bindir.mkdir()
            shutil.copy(LOCKCHECK, proj / "scripts" / "lockfile-check.py")
            (proj / "Package.swift").write_text("// manifest\n")
            if repo:
                subprocess.run([*GIT, "init", "-q"], cwd=proj, check=True)
            if committed is not None:
                (proj / "Package.resolved").write_text(committed)
            if repo:
                subprocess.run([*GIT, "add", "-A"], cwd=proj, check=True)
                if committed is not None and not track:
                    subprocess.run(
                        [*GIT, "rm", "-q", "--cached", "Package.resolved"], cwd=proj, check=True
                    )
            if worktree is not None:  # e.g. what `swift build` rewrote before the check
                (proj / "Package.resolved").write_text(worktree)
            env = {"PATH": f"{bindir}:/usr/bin:/bin"}
            if resolved is not None:
                Path(tmp, "resolved").write_text(resolved)
                env["RESOLVED"] = str(Path(tmp, "resolved"))
            stub = bindir / "swift"
            stub.write_text(SWIFT_STUB)
            stub.chmod(0o755)
            return subprocess.run(
                [sys.executable, "scripts/lockfile-check.py"],
                cwd=proj, env=env, capture_output=True, text=True, check=False,
            )  # fmt: skip

    def assert_exit(self, r, code, needle=""):
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        self.assertIn(needle, r.stdout + r.stderr)

    def test_nothing_to_pin_passes(self):
        self.assert_exit(self.check(), 0)

    def test_pins_with_no_committed_lockfile_fail(self):
        # also the case of remote packages reached through a local .package(path:)
        self.assert_exit(self.check(resolved=resolved_v3("swift-log")), 1, "not tracked")

    def test_current_tracked_lockfile_passes(self):
        lock = resolved_v3("swift-log")
        self.assert_exit(self.check(committed=lock, resolved=lock), 0)

    def test_format_rewrite_with_the_same_pins_passes(self):
        v3 = json.loads(resolved_v3("swift-log"))
        v2 = json.dumps({"pins": v3["pins"], "version": 2})
        self.assert_exit(self.check(committed=v2, resolved=json.dumps(v3)), 0)

    def test_stale_lockfile_fails(self):
        old = resolved_v3("swift-log")
        new = old.replace('"1.0.0"', '"1.1.0"')
        self.assert_exit(self.check(committed=old, resolved=new), 1, "stale")

    def test_stale_after_swift_build_rewrote_it_fails(self):
        old = resolved_v3("swift-log")
        new = old.replace('"1.0.0"', '"1.1.0"')
        self.assert_exit(self.check(committed=old, worktree=new, resolved=new), 1, "stale")

    def test_a_changed_location_is_stale(self):
        old = resolved_v3("swift-log")
        new = old.replace("github.com/example/", "github.com/fork/")
        self.assert_exit(self.check(committed=old, resolved=new), 1, "stale")

    def test_untracked_or_ignored_lockfile_fails(self):
        lock = resolved_v3("swift-log")
        self.assert_exit(self.check(committed=lock, resolved=lock, track=False), 1, "not tracked")

    def test_git_failure_is_an_error_not_a_finding(self):
        lock = resolved_v3("swift-log")
        self.assert_exit(self.check(committed=lock, resolved=lock, repo=False), 2)


class ExampleMatchesScaffoldTests(unittest.TestCase):
    def test_example_scripts_are_the_scaffolds(self):
        for script in sorted((SCAFFOLD / "scripts").iterdir()):
            with self.subTest(script=script.name):
                self.assertEqual(
                    (EXAMPLE / "scripts" / script.name).read_text(), script.read_text()
                )


if __name__ == "__main__":
    unittest.main()
