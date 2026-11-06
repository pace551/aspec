#!/usr/bin/env python3
"""Tests for the Swift branches of checks/sec-sca.sh and checks/sec-sast.sh.

Both picked their scanner by manifest and knew no Package.swift, so at T3+ a Swift
project hit "no recognized manifest" and failed SEC-SUPPLY-01 / SEC-SAST-01 in
/verify-compliance, even with templates/ci/swiftui.yml running both gates in CI.
checks/swift-project.py holds what both need to know about a Swift project:

- sec-sca: osv-scanner on every SwiftPM lockfile that pins something (the package's and
  Xcode's). Remote packages with no lockfile, or CocoaPods/Carthage lockfiles, can't be
  audited: that fails at strict tiers rather than passing with nothing checked.
- sec-sast: no Swift SAST scanner is free to run locally on private code (CodeQL's CLI
  license excludes it; semgrep's free engine finds little in Swift), so Swift's SAST
  runs in CI: the check passes when an enabled workflow job runs CodeQL on Swift. The
  workflows are parsed, not grepped, so a commented-out or disabled job doesn't count.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from hostile_tree import can_lock

ROOT = Path(__file__).resolve().parent.parent
SCA = ROOT / "checks" / "sec-sca.sh"
SAST = ROOT / "checks" / "sec-sast.sh"
HELPER = ROOT / "checks" / "swift-project.py"
SYSTEM_PATH = "/usr/bin:/bin"
XCODE_LOCK = "App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
PBXPROJ = "App.xcodeproj/project.pbxproj"
NO_DEPS = 'let package = Package(name: "A", targets: [.target(name: "A")])\n'
REMOTE_DEP = (
    "let package = Package(\n"
    '    name: "A",\n'
    "    dependencies: [\n"
    '        .package(url: "https://github.com/apple/swift-log.git", from: "1.5.0"),\n'
    "    ]\n"
    ")\n"
)
PINNED = json.dumps(
    {
        "pins": [
            {
                "identity": "swift-log",
                "kind": "remoteSourceControl",
                "location": "https://github.com/apple/swift-log.git",
                "state": {"revision": "abc", "version": "1.5.4"},
            }
        ],
        "version": 2,
    }
)
PINNED_V1 = json.dumps(
    {
        "object": {
            "pins": [
                {
                    "package": "swift-log",
                    "repositoryURL": "https://github.com/apple/swift-log.git",
                    "state": {"revision": "abc", "version": "1.5.4"},
                }
            ]
        },
        "version": 1,
    }
)
EMPTY_PINS = json.dumps({"pins": [], "version": 2})
REMOTE_PBXPROJ = (
    "/* Begin XCRemoteSwiftPackageReference section */\n"
    '\t\tAB12 /* XCRemoteSwiftPackageReference "swift-log" */ = {\n'
    "\t\t\tisa = XCRemoteSwiftPackageReference;\n"
    "\t\t};\n"
)
LOCAL_PBXPROJ = "// !$*UTF8*$!\n{ objects = { }; }\n"
ODD_SHAPE = "on: push\njobs:\n  x:\n    strategy: [1]\n    steps: 5\n"
CODEQL_SWIFT = """on: [push, pull_request]
jobs:
  sast:
    runs-on: macos-latest
    steps:
      - uses: github/codeql-action/init@v4
        with:
          languages: swift
      - uses: github/codeql-action/analyze@v4
"""


def stub(bindir: Path, name: str, log: Path, exit_code: int = 0) -> None:
    script = bindir / name
    script.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\nexit {exit_code}\n')
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


def run(
    script: Path,
    files: dict[str, str],
    tier: str,
    stubs=(),
    osv_exit: int = 0,
    subdir: str = "",
    lock: str = "",
):
    """Run a check on a fresh project; `subdir` puts it inside a git repo (a monorepo),
    `lock` names a path to make unreadable."""
    with tempfile.TemporaryDirectory() as tmp:
        repo, bindir, log = Path(tmp, "repo"), Path(tmp, "bin"), Path(tmp, "calls")
        bindir.mkdir()
        repo.mkdir()
        (repo / ".git").mkdir()
        for name, text in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text)
        for name in stubs:
            stub(bindir, name, log, osv_exit)
        locked = repo / lock if lock else None
        if locked:
            locked.chmod(0)
        try:
            proc = subprocess.run(
                ["bash", str(script), "--project", str(repo / subdir), "--tier", tier],
                env={**os.environ, "PATH": f"{bindir}:{SYSTEM_PATH}"},
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            if locked:
                locked.chmod(0o755 if locked.is_dir() else 0o644)
        return proc, log.read_text() if log.exists() else ""


class SwiftScaTests(unittest.TestCase):
    def assert_strict_fails_lenient_warns(self, files, needle, **kw):
        strict, calls = run(SCA, files, "T3", stubs=("osv-scanner",), **kw)
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn(needle, strict.stderr)
        lenient, _ = run(SCA, files, "T1", stubs=("osv-scanner",), **kw)
        self.assertEqual(lenient.returncode, 0, lenient.stdout + lenient.stderr)
        self.assertIn("WARNING", lenient.stderr)
        self.assertNotIn("no recognized manifest", lenient.stderr)
        return calls

    def test_package_without_remote_dependencies_has_nothing_to_audit(self):
        for manifest in (NO_DEPS, '// .package(url: "https://x.example/a.git", from: "1.0.0")\n'):
            with self.subTest(manifest=manifest):
                proc, calls = run(SCA, {"Package.swift": manifest}, "T3", stubs=("osv-scanner",))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("no pinned dependencies", proc.stdout)
                self.assertEqual(calls, "")

    def test_remote_dependencies_without_a_lockfile_fail_strict(self):
        self.assert_strict_fails_lenient_warns({"Package.swift": REMOTE_DEP}, "Package.resolved")

    def test_older_manifest_form_with_name_first_counts(self):
        manifest = (
            '.package(name: "Log", url: "https://github.com/apple/swift-log.git", from: "1.0.0")\n'
        )
        self.assert_strict_fails_lenient_warns({"Package.swift": manifest}, "Package.resolved")

    def test_xcode_remote_packages_without_a_lockfile_fail_strict(self):
        self.assert_strict_fails_lenient_warns({PBXPROJ: REMOTE_PBXPROJ}, "Package.resolved")

    def test_xcode_app_with_only_local_packages_has_nothing_to_audit(self):
        proc, calls = run(SCA, {PBXPROJ: LOCAL_PBXPROJ}, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(calls, "")

    def test_lockfiles_are_scanned(self):
        files = {
            "Package.swift": REMOTE_DEP,
            "Package.resolved": PINNED,
            PBXPROJ: REMOTE_PBXPROJ,
            XCODE_LOCK: PINNED_V1,
        }
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("--lockfile ./Package.resolved", calls)
        self.assertIn(f"--lockfile ./{XCODE_LOCK}", calls)

    def test_workspace_lockfile_covers_the_xcode_project(self):
        lock = "App.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        files = {PBXPROJ: REMOTE_PBXPROJ, lock: PINNED}
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"--lockfile ./{lock}", calls)

    def test_lockfile_with_no_pins_is_not_scanned(self):
        # osv-scanner exits 128 ("no packages found") on it
        files = {"Package.swift": NO_DEPS, "Package.resolved": EMPTY_PINS}
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(calls, "")

    def test_cocoapods_and_carthage_cant_be_audited(self):
        for lockfile in ("Podfile.lock", "Cartfile.resolved"):
            with self.subTest(lockfile=lockfile):
                files = {PBXPROJ: LOCAL_PBXPROJ, lockfile: "PODS:\n  - Alamofire (5.9.1)\n"}
                self.assert_strict_fails_lenient_warns(files, lockfile)

    def test_workspace_with_projects_in_subdirectories_is_recognized(self):
        lock = "App.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        files = {"App.xcworkspace/contents.xcworkspacedata": "<x/>\n", lock: PINNED}
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"--lockfile ./{lock}", calls)
        files = {
            "App.xcworkspace/contents.xcworkspacedata": "<x/>\n",
            f"App/{PBXPROJ}": REMOTE_PBXPROJ,
        }
        self.assert_strict_fails_lenient_warns(files, "Package.resolved")

    def test_nested_projects_and_packages(self):
        ws = "App.xcworkspace/contents.xcworkspacedata"
        ws_lock = "App.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        nested_project = f"Projects/App/{PBXPROJ}"
        # remote packages two levels down, nothing pinned anywhere: can't be audited
        for files in (
            {ws: "<x/>\n", nested_project: REMOTE_PBXPROJ},
            {ws: "<x/>\n", "Modules/Foo/Package.swift": REMOTE_DEP},
        ):
            with self.subTest(files=sorted(files)):
                self.assert_strict_fails_lenient_warns(files, "Package.resolved")
        # a modular app: the local package's remote dependencies are pinned by the workspace
        files = {ws: "<x/>\n", ws_lock: PINNED, "Modules/Foo/Package.swift": REMOTE_DEP}
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"--lockfile ./{ws_lock}", calls)
        # nested lockfiles are scanned; build output and vendored trees are not walked
        lock = f"Projects/App/{XCODE_LOCK}"
        files = {
            ws: "<x/>\n",
            nested_project: REMOTE_PBXPROJ,
            lock: PINNED,
            ".build/checkouts/x/Package.swift": REMOTE_DEP,
            ".build/checkouts/x/Package.resolved": PINNED,
            "Pods/Pods.xcodeproj/project.pbxproj": REMOTE_PBXPROJ,
        }
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(calls.strip(), f"osv-scanner scan source --lockfile ./{lock}")

    def test_version_specific_manifests_count(self):
        # SwiftPM picks Package@swift-6.0.swift over Package.swift on Swift 6
        files = {"Package.swift": NO_DEPS, "Package@swift-6.0.swift": REMOTE_DEP}
        self.assert_strict_fails_lenient_warns(files, "Package@swift-6.0.swift")

    def test_dependency_checkouts_are_not_walked(self):
        files = {
            "Package.swift": NO_DEPS,
            "SourcePackages/checkouts/dep/Package.swift": REMOTE_DEP,
            "SourcePackages/checkouts/dep/Example/Podfile.lock": "PODS:\n",
            "build/SourcePackages/checkouts/dep/Package.resolved": PINNED,
            "build/checkouts/dep/Package.swift": REMOTE_DEP,
        }
        proc, calls = run(SCA, files, "T3", stubs=("osv-scanner",))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(calls, "")

    def test_an_empty_lockfile_doesnt_hide_remote_packages(self):
        ws_lock = "App.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        for files in (
            {"Package.swift": REMOTE_DEP, "Package.resolved": EMPTY_PINS},
            {PBXPROJ: REMOTE_PBXPROJ, XCODE_LOCK: EMPTY_PINS},
            {PBXPROJ: REMOTE_PBXPROJ, ws_lock: EMPTY_PINS},
        ):
            with self.subTest(files=sorted(files)):
                self.assert_strict_fails_lenient_warns(files, "Package.resolved")

    def test_string_literals_and_comments_in_the_manifest(self):
        for manifest, remote in (
            ('let s = """\n.package(url: "x", from: "1")\n"""\n' + NO_DEPS, False),
            ('let s = #"say "hi" // not a comment"#\n' + REMOTE_DEP, True),
            ('/* .package(url: "x", from: "1") */\n' + NO_DEPS, False),
        ):
            with self.subTest(manifest=manifest):
                proc, _ = run(SCA, {"Package.swift": manifest}, "T3", stubs=("osv-scanner",))
                self.assertEqual(proc.returncode, 1 if remote else 0, proc.stdout + proc.stderr)

    def test_findings_fail(self):
        files = {"Package.swift": REMOTE_DEP, "Package.resolved": PINNED}
        proc, _ = run(SCA, files, "T3", stubs=("osv-scanner",), osv_exit=1)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_missing_scanner_fails_strict_and_warns_lenient(self):
        files = {"Package.swift": REMOTE_DEP, "Package.resolved": PINNED}
        strict, _ = run(SCA, files, "T3")
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn("osv-scanner", strict.stderr)
        lenient, _ = run(SCA, files, "T1")
        self.assertEqual(lenient.returncode, 0, lenient.stdout + lenient.stderr)
        self.assertIn("WARNING", lenient.stderr)
        self.assertNotIn("no recognized manifest", lenient.stderr)

    def test_unreadable_or_malformed_lockfile_is_incomplete(self):
        cases = [({"Package.resolved": "{not json"}, "")]
        if can_lock():
            cases.append(({"Package.resolved": PINNED}, "Package.resolved"))
        for extra, lock in cases:
            with self.subTest(lock=lock):
                files = {"Package.swift": REMOTE_DEP, **extra}
                proc, _ = run(SCA, files, "T3", stubs=("osv-scanner",), lock=lock)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


def codeql_job(languages: str, extra: str = "", strategy: str = "") -> str:
    return (
        "on: [push, pull_request]\njobs:\n  sast:\n    runs-on: macos-latest\n"
        f"{extra}{strategy}    steps:\n"
        "      - uses: github/codeql-action/init@v4\n"
        f"        with:\n          languages: {languages}\n"
        "      - uses: github/codeql-action/analyze@v4\n"
    )


class SwiftSastTests(unittest.TestCase):
    def check(self, workflow: str | None, tier: str = "T3", **kw):
        files = {"Package.swift": NO_DEPS}
        if workflow is not None:
            files[".github/workflows/ci.yml"] = workflow
        return run(SAST, files, tier, **kw)[0]

    def test_codeql_swift_job_in_ci_passes(self):
        for workflow in (
            CODEQL_SWIFT,
            codeql_job("javascript, swift"),
            codeql_job(
                "${{ matrix.language }}",
                strategy="    strategy:\n      matrix:\n        language: [javascript, swift]\n",
            ),
            codeql_job(
                "${{ matrix.language }}",
                strategy="    strategy:\n      matrix:\n        include:\n"
                "          - language: go\n          - language: swift\n",
            ),
        ):
            with self.subTest(workflow=workflow):
                proc = self.check(workflow)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("CodeQL", proc.stdout)

    def test_no_codeql_swift_job_fails_strict_and_warns_lenient(self):
        commented = "".join(
            f"# {line}\n"
            if "codeql" in line or "languages" in line or "with:" in line
            else line + "\n"
            for line in CODEQL_SWIFT.splitlines()
        )
        for name, workflow in {
            "none": None,
            "go": codeql_job("go"),
            "commented out": commented,
            "comment mentions swift": codeql_job("go # TODO swift"),
            "not a whole word": codeql_job("swiftlint-free"),
            "disabled": codeql_job("swift", extra="    if: false\n"),
            "disabled expression": codeql_job("swift", extra="    if: ${{ false }}\n"),
            "disabled, no spaces": codeql_job("swift", extra="    if: ${{false}}\n"),
            "init step disabled": CODEQL_SWIFT.replace(
                "      - uses: github/codeql-action/init@v4\n",
                "      - uses: github/codeql-action/init@v4\n        if: false\n",
            ),
            "analyze step disabled": CODEQL_SWIFT.replace(
                "      - uses: github/codeql-action/analyze@v4\n",
                "      - uses: github/codeql-action/analyze@v4\n        if: false\n",
            ),
            "swift excluded from the matrix": codeql_job(
                "${{ matrix.language }}",
                strategy="    strategy:\n      matrix:\n        language: [swift, go]\n"
                "        exclude:\n          - language: swift\n",
            ),
            "every swift combination excluded": codeql_job(
                "${{ matrix.language }}",
                strategy="    strategy:\n      matrix:\n        language: [swift, go]\n"
                "        os: [macos-latest, macos-15]\n        exclude:\n"
                "          - {language: swift, os: macos-latest}\n"
                "          - {language: swift, os: macos-15}\n",
            ),
            "a malformed include is ignored": codeql_job(
                "${{ matrix.lang }}",
                strategy="    strategy:\n      matrix:\n"
                "        lang: [go]\n        include: [swift]\n",
            ),
            "a later include overwrites swift": codeql_job(
                "${{ matrix.lang }}",
                strategy="    strategy:\n      matrix:\n        os: [macos-latest]\n"
                "        include:\n          - lang: swift\n          - lang: go\n",
            ),
            "manual trigger only": CODEQL_SWIFT.replace(
                "on: [push, pull_request]", "on: workflow_dispatch"
            ),
            "no trigger": CODEQL_SWIFT.replace("on: [push, pull_request]\n", ""),
            "API trigger only": CODEQL_SWIFT.replace(
                "[push, pull_request]", "[workflow_dispatch, repository_dispatch]"
            ),
            "no analyze step": CODEQL_SWIFT.replace("analyze", "upload-sarif"),
            "swift matrix, other job": codeql_job("go")
            + "  other:\n    runs-on: x\n    strategy:\n      matrix:\n"
            "        language: [swift]\n    steps:\n      - run: echo\n",
        }.items():
            with self.subTest(case=name):
                strict = self.check(workflow)
                self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
                self.assertIn("CodeQL", strict.stderr)
                lenient = self.check(workflow, tier="T1")
                self.assertEqual(lenient.returncode, 0, lenient.stdout + lenient.stderr)
                self.assertIn("WARNING", lenient.stderr)
                self.assertNotIn("no recognized manifest", lenient.stderr)

    def test_the_swiftui_ci_template_satisfies_it(self):
        template = (ROOT / "templates" / "ci" / "swiftui.yml").read_text()
        proc = self.check(template)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SEC-SAST-05", proc.stdout)

    def test_uploaded_results_pass_and_point_at_the_attestation(self):
        # whether code scanning blocks a merge is a repository setting, not in the checkout
        for upload in (
            "",
            "        with:\n          upload: always\n",
            "        with:\n"
            "          upload: ${{ github.event_name == 'push' && 'always' || 'never' }}\n",
            "        with:\n          upload: never\n          output: sarif-out\n"
            "      - uses: github/codeql-action/upload-sarif@v4\n"
            "        with:\n          sarif_file: sarif-out\n",
        ):
            with self.subTest(upload=upload):
                workflow = CODEQL_SWIFT.replace("analyze@v4\n", "analyze@v4\n" + upload)
                proc = self.check(workflow)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("SEC-SAST-05", proc.stdout)

    def test_kept_results_must_be_named_by_a_later_step(self):
        def kept(upload: str, after: str = "") -> str:
            return CODEQL_SWIFT.replace(
                "analyze@v4\n",
                f"analyze@v4\n        id: a\n        with:\n          upload: {upload}\n"
                f"          output: sarif-out\n{after}",
            )

        read_dir = "      - run: test -z \"$(jq '.runs[].results[]' sarif-out/*.sarif)\"\n"
        read_output = "      - run: check ${{ steps.a.outputs.sarif-output }}\n"
        read_too_early = CODEQL_SWIFT.replace(
            "      - uses: github/codeql-action/init@v4\n",
            "      - run: cat sarif-out/*.sarif\n      - uses: github/codeql-action/init@v4\n",
        ).replace(
            "analyze@v4\n",
            "analyze@v4\n        with:\n          upload: never\n          output: sarif-out\n",
        )
        long_read = (
            "      - run: echo checking the CodeQL results now, before anything else"
            " ${{ runner.temp }}/codeql-results/a.sarif && exit 1\n"
        )
        temp_kept = CODEQL_SWIFT.replace(
            "analyze@v4\n",
            "analyze@v4\n        with:\n          upload: never\n"
            "          output: ${{ runner.temp }}/codeql-results\n" + long_read,
        )
        env_read = (
            "      - env:\n          SARIF: ${{ steps.a.outputs.sarif-output }}\n"
            '        run: test -z "$(jq \'.runs[].results[]\' "$SARIF"/*.sarif)"\n'
        )
        artifact = (
            "      - uses: actions/upload-artifact@v4\n        with:\n          path: sarif-out\n"
        )
        runner_temp = CODEQL_SWIFT.replace(
            "analyze@v4\n",
            "analyze@v4\n        with:\n          upload: never\n"
            "          output: ${{runner.temp}}/results\n"
            '      - run: jq . "$RUNNER_TEMP/results/swift.sarif"\n',
        )
        # results that go somewhere pass (that they block a merge is SEC-SAST-05's
        # attestation, which no static reading of a workflow can settle); results that go
        # nowhere fail
        for name, workflow, passes in (
            ("never, results read", kept("never", read_dir), True),
            ("results read on a long line", temp_kept, True),
            ("false, sarif-output read", kept("false", read_output), True),
            ("sarif-output passed through env", kept("never", env_read), True),
            ("$RUNNER_TEMP path", runner_temp, True),
            ("kept as an artifact (attested)", kept("never", artifact), True),
            (
                "named inside a list",
                kept(
                    "never",
                    "      - uses: x/y@v1\n        with:\n"
                    "          files:\n            - sarif-out/a.sarif\n",
                ),
                True,
            ),
            (
                "bare upload-sarif (its default is analyze's default output)",
                CODEQL_SWIFT.replace(
                    "analyze@v4\n",
                    "analyze@v4\n        with:\n          upload: false\n"
                    "      - uses: github/codeql-action/upload-sarif@v4\n",
                ),
                True,
            ),
            (
                "output is an expression, repeated later",
                kept("never", "      - run: jq . ${{ env.OUT }}/*.sarif\n").replace(
                    "output: sarif-out", "output: ${{ env.OUT }}"
                ),
                True,
            ),
            (
                "parent directory named by an artifact upload",
                kept("never", artifact.replace("path: sarif-out", "path: sarif")).replace(
                    "output: sarif-out", "output: sarif/swift"
                ),
                True,
            ),
            ("empty upload value (codeql-action uploads)", kept(""), True),
            ("unknown upload value (codeql-action uploads)", kept("sometimes"), True),
            ("upload value in another case (codeql-action uploads)", kept("Never"), True),
            (
                "upload-sarif with a capitalized owner",
                CODEQL_SWIFT.replace(
                    "analyze@v4\n",
                    "analyze@v4\n        with:\n          upload: never\n"
                    "      - uses: GitHub/codeql-action/upload-sarif@v4\n",
                ),
                True,
            ),
            ("unbalanced quote isn't a constant", kept("${{ 'never }}"), True),
            ("unquoted false, nothing reads them", kept("false"), False),
            ("quoted 'false', nothing reads them", kept("'false'"), False),
            ("constant False keyword", kept("${{ False }}"), False),
            (
                "miscased path inside the action repo",
                CODEQL_SWIFT.replace(
                    "analyze@v4\n",
                    "analyze@v4\n        with:\n          upload: never\n"
                    "      - uses: github/codeql-action/Upload-Sarif@v4\n",
                ),
                False,
            ),
            ("constant false expression", kept("${{ false }}"), False),
            ("constant 'never' expression", kept("${{ 'never' }}"), False),
            ("never, nothing reads them", kept("never"), False),
            ("failure-only, nothing reads them", kept("failure-only"), False),
            ("read before analyze runs", read_too_early, False),
            (
                "output ./ and an unrelated step",
                kept("never", "      - run: echo done\n").replace(
                    "output: sarif-out", "output: ./"
                ),
                False,
            ),
            (
                "short output name inside another step",
                kept(
                    "never", "      - uses: actions/checkout@v4\n      - run: echo checkout\n"
                ).replace("output: sarif-out", "output: out"),
                False,
            ),
        ):
            with self.subTest(case=name):
                proc = self.check(workflow)
                self.assertEqual(proc.returncode, 0 if passes else 1, proc.stdout + proc.stderr)

    def test_workflows_at_the_repository_root_count(self):
        files = {"apps/ios/Package.swift": NO_DEPS, ".github/workflows/ci.yml": CODEQL_SWIFT}
        proc, _ = run(SAST, files, "T3", subdir="apps/ios")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_a_subprojects_own_workflows_dont_run(self):
        # GitHub runs only the repository root's .github/workflows
        files = {
            "apps/ios/Package.swift": NO_DEPS,
            "apps/ios/.github/workflows/ci.yml": CODEQL_SWIFT,
        }
        proc, _ = run(SAST, files, "T3", subdir="apps/ios")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_triggers_in_their_other_forms(self):
        for on in (
            "on: push",
            "on:\n  pull_request:\n    branches: [main]",
            "on:\n  schedule:\n    - cron: '0 0 * * 0'",
        ):
            with self.subTest(on=on):
                proc = self.check(CODEQL_SWIFT.replace("on: [push, pull_request]", on))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_other_shapes_github_runs_on_its_own(self):
        reusable_caller = "on: push\njobs:\n  sast:\n    uses: ./.github/workflows/codeql.yml\n"
        reusable = CODEQL_SWIFT.replace("on: [push, pull_request]", "on: workflow_call")
        for name, workflows in {
            "reusable workflow": {"ci.yml": reusable_caller, "codeql.yml": reusable},
            "pull_request_target": {
                "ci.yml": CODEQL_SWIFT.replace("[push, pull_request]", "pull_request_target")
            },
            "after a skipped job, if: always()": {
                "ci.yml": codeql_job("swift", extra="    needs: gate\n    if: always()\n")
                + "  gate:\n    if: false\n    runs-on: x\n    steps:\n      - run: echo\n"
            },
            "one swift combination left": {
                "ci.yml": codeql_job(
                    "${{ matrix.language }}",
                    strategy="    strategy:\n      matrix:\n        language: [swift, go]\n"
                    "        os: [macos-latest, macos-15]\n        exclude:\n"
                    "          - {language: swift, os: macos-latest}\n",
                )
            },
            "an include that can't merge adds a job": {
                "ci.yml": codeql_job(
                    "${{ matrix.lang }}",
                    strategy="    strategy:\n      matrix:\n        lang: [go]\n"
                    "        include:\n          - lang: swift\n",
                )
            },
            "include after exclude": {
                "ci.yml": codeql_job(
                    "${{ matrix.language }}",
                    strategy="    strategy:\n      matrix:\n        language: [swift, go]\n"
                    "        exclude:\n          - language: swift\n"
                    "        include:\n          - language: swift\n",
                )
            },
        }.items():
            with self.subTest(case=name):
                files = {"Package.swift": NO_DEPS}
                files.update({f".github/workflows/{k}": v for k, v in workflows.items()})
                proc, _ = run(SAST, files, "T3")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_a_broken_workflow_doesnt_hide_a_working_one(self):
        files = {
            "Package.swift": NO_DEPS,
            ".github/workflows/a-broken.yml": "jobs: [unclosed\n",
            ".github/workflows/b-odd.yml": ODD_SHAPE,
            ".github/workflows/codeql.yml": CODEQL_SWIFT,
        }
        proc, _ = run(SAST, files, "T3")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_xcode_app_without_package_swift_is_recognized(self):
        files = {PBXPROJ: LOCAL_PBXPROJ, ".github/workflows/ci.yml": CODEQL_SWIFT}
        proc, _ = run(SAST, files, "T3")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_unreadable_or_malformed_workflow_is_incomplete(self):
        anchor_loop = CODEQL_SWIFT.replace(
            "analyze@v4\n",
            "analyze@v4\n        with:\n          upload: never\n      - &a {x: [*a]}\n",
        )
        for workflow in (
            anchor_loop,
            "jobs: [unclosed\n",
            ODD_SHAPE,
        ):
            with self.subTest(workflow=workflow):
                for tier in ("T1", "T3"):
                    self.assertEqual(self.check(workflow, tier=tier).returncode, 2)
        if can_lock():
            proc = self.check(CODEQL_SWIFT, lock=".github/workflows/ci.yml")
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


class HelperTests(unittest.TestCase):
    """swift-project.py on its own: what the two scripts' fixtures don't reach."""

    def helper(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(ROOT / ".venv" / "bin" / "python"), str(HELPER), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.helper(Path(tmp), "nope").returncode, 2)

    def test_outside_a_git_repo_the_projects_own_workflows_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".github" / "workflows").mkdir(parents=True)
            (Path(tmp) / ".github" / "workflows" / "ci.yml").write_text(CODEQL_SWIFT)
            self.assertEqual(self.helper(Path(tmp), "codeql").returncode, 0)

    def test_files_on_disk_count_committed_or_not(self):
        # /verify-compliance runs on the working tree: a manifest not yet committed, or one
        # in a submodule (which git's index lists as a single entry), still counts
        git = ("git", "-c", "user.name=t", "-c", "user.email=t@example.com")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run([*git, "init", "-q"], cwd=repo, check=True)
            (repo / "Package.swift").write_text(NO_DEPS)
            (repo / "Vendor" / "Lib").mkdir(parents=True)
            (repo / "Vendor" / "Lib" / ".git").write_text("gitdir: ../../.git/modules/Lib\n")
            (repo / "Vendor" / "Lib" / "Package.swift").write_text(REMOTE_DEP)
            self.assertEqual(
                self.helper(repo, "sca").stdout, "unpinned ./Vendor/Lib/Package.swift\n"
            )

    def test_a_path_with_a_newline_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a\nb").mkdir()
            (Path(tmp) / "a\nb" / "Package.resolved").write_text(PINNED)
            self.assertEqual(self.helper(Path(tmp), "sca").returncode, 2)

    @unittest.skipUnless(can_lock(), "chmod 000 stops nobody when running as root")
    def test_unreadable_directories_are_incomplete(self):
        for mode, locked in (("sca", "Sources"), ("codeql", ".github/workflows")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / ".git").mkdir()
                (Path(tmp) / locked).mkdir(parents=True)
                (Path(tmp) / locked).chmod(0)
                try:
                    self.assertEqual(self.helper(Path(tmp), mode).returncode, 2)
                finally:
                    (Path(tmp) / locked).chmod(0o755)

    def test_a_matrix_from_an_expression_isnt_followed(self):
        workflow = codeql_job(
            "${{ matrix.language }}",
            strategy="    strategy:\n      matrix: ${{ fromJSON(needs.setup.outputs.m) }}\n",
        )
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            (Path(tmp) / ".github" / "workflows").mkdir(parents=True)
            (Path(tmp) / ".github" / "workflows" / "ci.yml").write_text(workflow)
            self.assertEqual(self.helper(Path(tmp), "codeql").returncode, 3)


class LenientSkipMessageTests(unittest.TestCase):
    def test_a_skipped_scanner_is_not_reported_as_no_manifest(self):
        files = {"pyproject.toml": '[project]\nname = "x"\nversion = "0"\n'}
        for script in (SCA, SAST):
            with self.subTest(script=script.name):
                proc, _ = run(script, files, "T1")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("WARNING", proc.stderr)
                self.assertNotIn("no recognized manifest", proc.stderr)


if __name__ == "__main__":
    unittest.main()
