#!/usr/bin/env python3
"""Tests for how import-cycles.py and silent-swallow.py walk a project.

Both must treat a directory they can't read as an incomplete scan (exit 2), never as an
empty one, without tripping over directories that aren't theirs to scan: a gitignored,
unreadable top-level directory (a Docker volume) isn't a package, and a first-party
subpackage named `build` or `dist` is still first-party.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from hostile_tree import can_lock, clean_env, tree

ROOT = Path(__file__).resolve().parent.parent
IMPORT_CYCLES = ROOT / "checks" / "import-cycles.py"
SILENT_SWALLOW = ROOT / "checks" / "silent-swallow.py"
SWALLOW = "try:\n    x = 1\nexcept Exception:\n    pass\n"


def run(script: Path, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), "--project", str(project)],
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )


class ImportCyclesWalkTests(unittest.TestCase):
    def test_cycle_through_a_subpackage_named_build_is_found(self):
        with tree() as t:
            t.write({
                "pkg/__init__.py": "",
                "pkg/a.py": "from pkg.build import b\n",
                "pkg/build/__init__.py": "",
                "pkg/build/b.py": "from pkg import a\n",
            })  # fmt: skip
            r = run(IMPORT_CYCLES, t.root)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("pkg.build.b", r.stdout)

    def test_absolute_src_outside_the_project_is_scanned(self):
        with tree() as proj, tree() as lib:
            lib.write({
                "pkg/__init__.py": "",
                "pkg/a.py": "from pkg import b\n",
                "pkg/b.py": "from pkg import a\n",
            })  # fmt: skip
            proj.write({"README": "x\n"}).commit()
            r = subprocess.run(
                [sys.executable, str(IMPORT_CYCLES), "--project", str(proj.root),
                 "--src", str(lib.root)],
                capture_output=True, text=True, env=clean_env(), check=False,
            )  # fmt: skip
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_symlinked_src_is_scanned(self):
        with tree() as t:
            t.write({
                "real/pkg/__init__.py": "",
                "real/pkg/a.py": "from pkg import b\n",
                "real/pkg/b.py": "from pkg import a\n",
            })  # fmt: skip
            (t.root / "src").symlink_to("real", target_is_directory=True)
            t.commit()
            r = run(IMPORT_CYCLES, t.root)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("import cycle", r.stdout, r.stderr)

    @unittest.skipUnless(can_lock(), "root can read any directory")
    def test_unreadable_gitignored_top_level_dir_is_not_a_package(self):
        with tree() as t:
            t.write(
                {"pkg/__init__.py": "", "pkg/a.py": "", "pgdata/x": "", ".gitignore": "pgdata/\n"}
            )
            t.commit()
            with t.locked("pgdata"):
                r = run(IMPORT_CYCLES, t.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(can_lock(), "root can read any directory")
    def test_unreadable_gitignored_dir_inside_src_is_skipped(self):
        with tree() as t:
            t.write({
                "src/pkg/__init__.py": "",
                "src/pkg/a.py": "",
                "src/pkg/.pytest_cache/x": "",
                ".gitignore": ".pytest_cache/\n",
            })  # fmt: skip
            t.commit()
            with t.locked("src/pkg/.pytest_cache"):
                r = run(IMPORT_CYCLES, t.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(can_lock(), "root can read any directory")
    def test_force_added_package_in_an_ignored_unreadable_dir_is_incomplete(self):
        with tree() as t:
            t.write({
                "pkg/__init__.py": "",
                "pkg/a.py": "from generated import models\n",
                "generated/__init__.py": "",
                "generated/models.py": "from pkg import a\n",
                ".gitignore": "generated/\n",
            })  # fmt: skip
            t.git("init", "-q")
            t.git("add", "-f", "-A")
            t.commit()
            with t.locked("generated"):
                r = run(IMPORT_CYCLES, t.root)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    @unittest.skipUnless(can_lock(), "root can read any directory")
    def test_unreadable_unignored_top_level_dir_is_incomplete(self):
        with tree() as t:
            t.write({"pkg/__init__.py": "", "pkg/a.py": "", "other/__init__.py": ""})
            t.commit()
            with t.locked("other"):
                r = run(IMPORT_CYCLES, t.root)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


@unittest.skipUnless(can_lock(), "root can read any directory")
class SilentSwallowWalkTests(unittest.TestCase):
    def test_outside_git_an_unreadable_dir_is_incomplete(self):
        with tree() as t:
            t.write({"app/job.py": SWALLOW, "ok.py": "x = 1\n"})
            with t.locked("app"):
                r = run(SILENT_SWALLOW, t.root)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_git_failing_inside_a_repo_is_incomplete_not_a_walk(self):
        with tree() as t:
            t.write({"a.py": "x = 1\n"})
            t.commit()
            index = t.root / ".git" / "index"
            index.chmod(0)
            try:
                r = run(SILENT_SWALLOW, t.root)
            finally:
                index.chmod(0o644)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_outside_git_a_nested_build_dir_is_scanned(self):
        with tree() as t:
            t.write({"app/build/steps.py": SWALLOW})
            r = run(SILENT_SWALLOW, t.root)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_unreadable_files_are_reported_alongside_findings(self):
        with tree() as t:
            t.write({"a.py": SWALLOW, "locked/b.py": SWALLOW})
            t.commit()
            with t.locked("locked"):
                r = run(SILENT_SWALLOW, t.root)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("a.py", r.stdout)
        self.assertIn("scan incomplete", r.stderr)


if __name__ == "__main__":
    unittest.main()
