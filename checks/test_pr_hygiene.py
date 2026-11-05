#!/usr/bin/env python3
"""Unit tests for pr-hygiene.py: ASPEC's own PR rules as a check.

A PR is one squashed commit with a conventional-commit subject, and a `feat`, `fix` or
breaking change adds to CHANGELOG.md's `## Unreleased` section. (Bot PRs are skipped by the
CI job, not here.) Each test builds a throwaway repo with a `main` branch.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "checks" / "pr-hygiene.py"
GIT = ["git", "-c", "init.defaultBranch=main"]
HUMAN = ["-c", "user.name=t", "-c", "user.email=t@t"]


HOOK_ARGS = ("origin", "https://example.invalid/r.git")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [*GIT, *HUMAN, *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


CHANGELOG = """# Changelog

## Unreleased

## 0.1.0 — 2026-11-01

- First release.
"""


class PrHygieneTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        (self.repo / "CHANGELOG.md").write_text(CHANGELOG)
        self.commit("chore: initial", "CHANGELOG.md")
        self.git("switch", "-qc", "feature")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return git(self.repo, *args)

    def commit(self, message: str, *files: str) -> None:
        for name in files or ("work.txt",):
            path = self.repo / name
            if name != "CHANGELOG.md":
                path.write_text(path.read_text() + "x" if path.exists() else "x")
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def add_changelog(self, line: str, heading: str = "## Unreleased") -> None:
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace(heading + "\n", f"{heading}\n\n{line}\n", 1))

    def check(self, base: str = "main") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--base", base, "--head", "HEAD"],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_passes(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def assert_fails(self, needle: str):
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(needle, r.stdout + r.stderr)

    def test_no_commits_passes(self):
        self.assert_passes()

    def test_single_docs_commit_without_changelog_passes(self):
        self.commit("docs: explain the hook")
        self.assert_passes()

    def test_two_commits_fail(self):
        self.commit("docs: explain the hook")
        self.commit("docs: fix a typo")
        self.assert_fails("2 commits")

    def test_non_conventional_subject_fails(self):
        self.commit("Update the hook")
        self.assert_fails("conventional")

    def test_feat_without_changelog_fails(self):
        self.commit("feat: add a check")
        self.assert_fails("## Unreleased")

    def test_fix_with_unreleased_entry_passes(self):
        self.add_changelog("- Fixed the check.")
        self.commit("fix(checks): handle spaced paths", "CHANGELOG.md")
        self.assert_passes()

    def test_scoped_feat_with_unreleased_entry_passes(self):
        self.add_changelog("- New check.")
        self.commit("feat(lint): add a check", "CHANGELOG.md")
        self.assert_passes()

    def test_fix_editing_a_released_section_only_fails(self):
        self.add_changelog("- Late note.", heading="## 0.1.0 — 2026-11-01")
        self.commit("fix: handle spaced paths", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_reverting_an_unreleased_feat_removes_its_entry(self):
        # DEV-GIT-01 accepts git's own `Revert "..."` subject
        self.put_on_main("- Adds a check.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Adds a check.\n", ""))
        self.commit('Revert "feat: add a check"\n\nThis reverts commit 0123abc.', "CHANGELOG.md")
        self.assert_passes()

    def test_reverting_a_released_fix_needs_an_entry(self):
        self.commit('Revert "fix: keep spaced paths whole"\n\nThis reverts commit 0123abc.')
        self.assert_fails("## Unreleased")
        self.git("reset", "-q", "--hard", "main")
        self.add_changelog("- Reverts the spaced-path fix from 0.3.1; it broke X.")
        self.commit('Revert "fix: keep spaced paths whole"', "CHANGELOG.md")
        self.assert_passes()

    def test_reverting_a_footer_breaking_change_needs_an_entry(self):
        self.add_changelog("- Renames the hashes file.")
        self.commit("refactor: rename the hashes file\n\nBREAKING CHANGE: new name", "CHANGELOG.md")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        self.commit(f'Revert "refactor: rename the hashes file"\n\nThis reverts commit {sha}.')
        self.assert_fails("reverting an unreleased breaking change")

    def breaking_chain(self) -> list[str]:
        """A footer-breaking refactor on main, then shas of revert, reapply, revert."""
        self.add_changelog("- Renames the hashes file.")
        self.commit("refactor: rename the hashes file\n\nBREAKING CHANGE: new name", "CHANGELOG.md")
        shas = [self.git("rev-parse", "HEAD").strip()]
        original = "refactor: rename the hashes file"
        # the subjects git (2.43+) writes for each successive `git revert`
        for subject in (
            f'Revert "{original}"',
            f'Reapply "{original}"',
            f'Revert "Reapply "{original}""',
        ):
            self.commit(f"{subject}\n\nThis reverts commit {shas[-1]}.")
            shas.append(self.git("rev-parse", "HEAD").strip())
        return shas

    def check_tip(self, base: str, head: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--base", base, "--head", head],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_reapplying_a_footer_breaking_change_needs_an_entry(self):
        shas = self.breaking_chain()
        r = self.check_tip(shas[1], shas[2])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("breaking change needs", r.stdout)

    def test_revert_chain_is_followed_to_the_original(self):
        shas = self.breaking_chain()
        r = self.check_tip(shas[2], shas[3])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("reverting an unreleased breaking change", r.stdout)

    def test_a_revert_keeps_its_own_breaking_footer(self):
        self.commit("refactor: add g")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        self.commit(
            f'Revert "refactor: add g"\n\nThis reverts commit {sha}.\n\nBREAKING CHANGE: g is gone'
        )
        self.assert_fails("a breaking change needs new text")

    def land_feat_on_main(self) -> str:
        """A feat with its Unreleased entry, merged to main; returns its sha."""
        self.add_changelog("- Adds a check.")
        self.commit("feat: add a check", "CHANGELOG.md")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        return sha

    def test_reverting_an_unreleased_feat_must_drop_its_entry(self):
        sha = self.land_feat_on_main()
        self.add_changelog("- Reverts the new check.")  # the feat's entry stays
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_fails("remove its entry")

    def test_reverting_an_unreleased_feat_by_dropping_its_entry_passes(self):
        sha = self.land_feat_on_main()
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Adds a check.\n", ""))
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def test_reverting_a_released_feat_needs_a_new_entry(self):
        sha = self.land_feat_on_main()
        path = self.repo / "CHANGELOG.md"  # release it: Unreleased becomes 0.2.0
        path.write_text(
            path.read_text().replace("## Unreleased\n", "## Unreleased\n\n## 0.2.0\n", 1)
        )
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "chore(main): release 0.2.0")
        self.git("branch", "-f", "main")
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.')
        self.assert_fails("add an entry")
        self.git("reset", "-q", "--hard", "main")
        self.add_changelog("- Reverts the check added in 0.2.0.")
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def release_main(self, version: str) -> None:
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace("## Unreleased\n", f"## Unreleased\n\n## {version}\n", 1)
        )
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"chore(main): release {version}")
        self.git("branch", "-f", "main")

    def test_reverting_a_reworded_unreleased_entry_by_dropping_it_passes(self):
        sha = self.land_feat_on_main()
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace("- Adds a check.", "- Adds a lint gate (LINT-01).")
        )
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs: reword the entry")
        self.git("branch", "-f", "main")
        path.write_text(path.read_text().replace("- Adds a lint gate (LINT-01).\n", ""))
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def test_released_entry_words_reused_later_still_count_as_released(self):
        sha = self.land_feat_on_main()
        self.release_main("0.2.0")
        self.put_on_main("- Adds a scan and a check.")
        self.add_changelog("- Reverts the check added in 0.2.0.")
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def test_reverting_an_unreleased_reapply_of_a_released_feat(self):
        sha = self.land_feat_on_main()
        self.release_main("0.2.0")
        self.add_changelog("- Reverts the check.")
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        revert = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        self.release_main("0.3.0")
        self.add_changelog("- Restores the check, now fixed.")
        self.commit(f'Reapply "feat: add a check"\n\nThis reverts commit {revert}.', "CHANGELOG.md")
        reapply = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Restores the check, now fixed.\n", ""))
        self.commit(
            f'Revert "Reapply "feat: add a check""\n\nThis reverts commit {reapply}.',
            "CHANGELOG.md",
        )
        self.assert_passes()

    def test_reverting_must_drop_its_own_entry_not_another(self):
        sha = self.land_feat_on_main()
        self.put_on_main("- Repairs the scanner.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Repairs the scanner.\n", ""))
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_fails("remove its entry")

    def test_a_revert_note_reusing_the_entrys_words_passes(self):
        sha = self.land_feat_on_main()
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Adds a check.", "- Reverts a check."))
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def test_rewrapping_the_reverted_entry_does_not_remove_it(self):
        self.add_changelog("- Adds a check that is long enough\n  to wrap.")
        self.commit("feat: add a check", "CHANGELOG.md")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- Adds a check that is long enough\n  to wrap.",
                "- Adds a check that is\n  long enough to wrap.",
            )
        )
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_fails("remove its entry")

    def test_dropping_one_of_two_identical_entries_passes(self):
        self.put_on_main("- Improves checks.")
        self.add_changelog("- Improves checks.")
        self.commit("feat: improve checks", "CHANGELOG.md")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Improves checks.\n", "", 1))
        self.commit(f'Revert "feat: improve checks"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def test_deleting_part_of_the_reverted_entry_fails(self):
        self.add_changelog("- Adds a check.\n  It scans spaced paths.")
        self.commit("feat: add a check", "CHANGELOG.md")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("  It scans spaced paths.\n", ""))
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_fails("remove its entry")

    def test_a_shared_subheading_the_feat_added_may_stay(self):
        self.add_changelog("### Added\n\n- Adds a check.")
        self.commit("feat: add a check", "CHANGELOG.md")
        sha = self.git("rev-parse", "HEAD").strip()
        self.git("branch", "-f", "main")
        path = self.repo / "CHANGELOG.md"  # another entry now lives under the heading
        path.write_text(
            path.read_text().replace("- Adds a check.\n", "- Adds a check.\n- Adds a scan.\n")
        )
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs: another entry")
        self.git("branch", "-f", "main")
        path.write_text(path.read_text().replace("- Adds a check.\n", ""))
        self.commit(f'Revert "feat: add a check"\n\nThis reverts commit {sha}.', "CHANGELOG.md")
        self.assert_passes()

    def test_reverting_a_docs_change_needs_no_entry(self):
        self.commit('Revert "docs: explain the hook"')
        self.assert_passes()

    def test_reapplying_a_feat_needs_an_entry(self):
        for subject in ('Reapply "feat: add a check"', 'Revert "Revert "feat: add a check""'):
            with self.subTest(subject=subject):
                self.git("reset", "-q", "--hard", "main")
                self.commit(subject)
                self.assert_fails("## Unreleased")

    def test_revert_of_a_non_conventional_subject_fails(self):
        self.commit('Revert "Update stuff"')
        self.assert_fails("conventional")

    def test_breaking_change_needs_changelog(self):
        self.commit("refactor!: rename the hashes file")
        self.assert_fails("breaking change needs")

    def test_breaking_change_footer_needs_changelog(self):
        self.commit("refactor: rename the hashes file\n\nBREAKING CHANGE: new file name")
        self.assert_fails("breaking change needs")

    def test_breaking_change_footer_with_changelog_passes(self):
        self.add_changelog("- Renamed the hashes file.")
        self.commit("refactor: rename it\n\nBREAKING-CHANGE: new name", "CHANGELOG.md")
        self.assert_passes()

    def test_deleting_an_unreleased_entry_is_not_adding_one(self):
        self.put_on_main("- Someone else's entry.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Someone else's entry.\n", ""))
        self.commit("fix: handle spaced paths", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def put_on_main(self, entry: str) -> None:
        """Commit an Unreleased entry and make that commit the base."""
        self.add_changelog(entry)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs: entry on main")
        self.git("branch", "-f", "main")

    def test_rewrapping_an_existing_entry_is_not_adding_one(self):
        self.put_on_main("- An existing entry that is long enough\n  to wrap onto two lines.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- An existing entry that is long enough\n  to wrap onto two lines.",
                "- An existing entry\n  that is long enough to wrap onto two lines.",
            )
        )
        self.commit("feat: new gate", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_a_heading_alone_is_not_text(self):
        self.put_on_main("- An existing entry.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- An existing entry.\n", "### Fixed\n\n- An existing entry.\n"
            )
        )
        self.commit("feat: new gate", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_a_bare_bullet_is_not_text(self):
        self.add_changelog("- ")
        self.commit("feat: new gate", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_unindented_rewrap_is_not_text(self):
        self.put_on_main("- Foo bar\n  baz qux.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(path.read_text().replace("- Foo bar\n  baz qux.", "- Foo bar\nbaz qux."))
        self.commit("feat: new gate", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_any_list_style_or_prose_counts(self):
        for entry in ("* New check.", "+ New check.", "1. New check.", "A paragraph of prose."):
            with self.subTest(entry=entry):
                self.git("reset", "-q", "--hard", "main")
                self.add_changelog(entry)
                self.commit("feat: new check", "CHANGELOG.md")
                self.assert_passes()

    def test_reordering_entries_is_not_text(self):
        self.put_on_main("- First entry here.\n- Second entry there.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- First entry here.\n- Second entry there.",
                "- Second entry there.\n- First entry here.",
            )
        )
        self.commit("feat: new gate", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_a_line_starting_with_a_hash_is_text(self):
        self.put_on_main("- Fixes the scanner, see")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- Fixes the scanner, see\n",
                "- Fixes the scanner, see\n#38 for paths with spaces.\n",
            )
        )
        self.commit("fix: spaced paths", "CHANGELOG.md")
        self.assert_passes()

    def test_an_indented_heading_is_not_text(self):
        self.put_on_main("- An existing entry.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- An existing entry.\n", "   ### Added\n\n- An existing entry.\n"
            )
        )
        self.commit("feat: new gate", "CHANGELOG.md")
        self.assert_fails("## Unreleased")

    def test_sub_bullet_after_a_blank_line_counts(self):
        self.put_on_main("- An existing entry.")
        path = self.repo / "CHANGELOG.md"
        path.write_text(
            path.read_text().replace(
                "- An existing entry.\n", "- An existing entry.\n\n  - Also covers spaces.\n"
            )
        )
        self.commit("fix: spaced paths", "CHANGELOG.md")
        self.assert_passes()

    def test_new_entry_worded_like_an_old_one_counts(self):
        self.put_on_main("- Pins the toolchain.")
        self.add_changelog("- Pins the toolchain.")
        self.commit("fix: pin the CI toolchain too", "CHANGELOG.md")
        self.assert_passes()

    def test_dependency_subject_does_not_exempt_later_commits(self):
        self.commit("chore(deps): bump ruff")
        self.commit("feat: new gate")
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("2 commits", r.stdout)
        self.assertIn("feat change needs", r.stdout)

    def test_bot_author_name_is_not_an_exemption(self):
        subprocess.run(
            [
                *GIT,
                "-c",
                "user.name=x[bot]",
                "-c",
                "user.email=x@x",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "Not conventional",
            ],
            cwd=self.repo,
            capture_output=True,
            check=True,
        )
        self.assert_fails("conventional")

    def test_merge_base_is_used_not_main_tip(self):
        self.commit("docs: explain the hook")
        self.git("switch", "-q", "main")
        self.commit("docs: unrelated change on main")
        self.git("switch", "-q", "feature")
        self.assert_passes()

    def test_unknown_base_is_an_error(self):
        self.commit("docs: explain the hook")
        r = self.check(base="nope")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


class PrePushScriptTests(unittest.TestCase):
    """scripts/pre-push.sh: hook mode checks each pushed branch, by hand it checks HEAD."""

    ZERO = "0" * 40

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        for rel in ("scripts/pre-push.sh", "scripts/venv.sh", "checks/pr-hygiene.py"):
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, self.repo / rel)
        if sys.prefix != sys.base_prefix:  # the venv running these tests, whole
            (self.repo / ".venv").symlink_to(sys.prefix, target_is_directory=True)
        else:  # no venv: pr-hygiene.py needs only the standard library
            (self.repo / ".venv" / "bin").mkdir(parents=True)
            (self.repo / ".venv" / "bin" / "python").symlink_to(sys.executable)
        test_sh = self.repo / "scripts" / "test.sh"
        test_sh.write_text("#!/bin/sh\nexit 0\n")
        test_sh.chmod(0o755)
        (self.repo / "CHANGELOG.md").write_text(CHANGELOG)
        (self.repo / ".gitignore").write_text(".venv\n")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "chore: initial")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("switch", "-qc", "feature")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return git(self.repo, *args).strip()

    def commit(self, message: str) -> str:
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def pre_push(self, *args: str, refs: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(self.repo / "scripts" / "pre-push.sh"), *args],
            cwd=self.repo,
            input=refs,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_by_hand_checks_head(self):
        self.commit("docs: one")
        self.assertEqual(self.pre_push().returncode, 0)
        self.commit("docs: two")
        r = self.pre_push()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("2 commits", r.stdout)

    def test_hook_checks_a_branch_pushed_as_head(self):
        # `git push origin HEAD` reports the local ref as HEAD
        self.commit("docs: one")
        sha = self.commit("docs: two")
        self.git("switch", "-q", "main")
        r = self.pre_push(*HOOK_ARGS, refs=f"HEAD {sha} refs/heads/feature {self.ZERO}\n")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("2 commits", r.stdout)

    def test_hook_checks_the_pushed_branch_not_head(self):
        bad = self.commit("Not conventional")
        self.git("switch", "-q", "main")
        line = f"refs/heads/feature {bad} refs/heads/feature {self.ZERO}\n"
        r = self.pre_push(*HOOK_ARGS, refs=line)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_hook_passes_a_clean_branch(self):
        sha = self.commit("docs: one")
        line = f"refs/heads/feature {sha} refs/heads/feature {self.ZERO}\n"
        r = self.pre_push(*HOOK_ARGS, refs=line)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_hook_skips_tags_and_deletions(self):
        self.commit("docs: one")
        sha = self.commit("docs: two")
        refs = (
            f"refs/tags/v1 {sha} refs/tags/v1 {self.ZERO}\n"
            f"(delete) {self.ZERO} refs/heads/old {sha}\n"
        )
        r = self.pre_push(*HOOK_ARGS, refs=refs)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_hook_with_no_ref_lines_checks_nothing(self):
        # git runs pre-push with empty stdin when every ref is up to date
        self.commit("docs: one")
        self.commit("docs: two")
        r = self.pre_push(*HOOK_ARGS, refs="")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_scaffold_hook_forwards_args_and_refs(self):
        self.commit("docs: one")
        sha = self.commit("docs: two")
        line = f"refs/heads/feature {sha} refs/heads/feature {self.ZERO}\n"
        r = subprocess.run(
            [
                "bash",
                str(ROOT / "templates/scaffolds/_common/githooks/pre-push"),
                *HOOK_ARGS,
            ],
            cwd=self.repo,
            input=line,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("2 commits", r.stdout)


if __name__ == "__main__":
    unittest.main()
