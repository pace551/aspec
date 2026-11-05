#!/usr/bin/env python3
"""Tests that ASPEC's shell pipelines hand file lists to xargs NUL-separated.

Plain `xargs` splits its input on whitespace, so a path with a space becomes two
nonexistent paths. /evolve-standards' candidate search found no learning notes at all,
because every note /harvest-learnings writes is named `YYYY-MM-DD governance <slug>.md`.
INF-ENVS, INF-CONTAINERS and INF-SERVERLESS passed a noncompliant file whose path had a
space, since grep -L only reported errors for the split halves. Producers now emit
NUL-separated lists (`-0`, `--null`, `-z`), xargs reads them with `-0`, and
lint-framework rejects an xargs without `-0`/`--null` in standards and skills.
The candidate search uses grep on both sides: inside Claude Code `rg` can be a shell
function, which xargs cannot exec.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "lint_framework", ROOT / "checks" / "lint-framework.py"
)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

UNSAFE = [
    'rg -l "type: governance-learning" $VAULT/ | \\\n  xargs rg -l "status: candidate"',
    '! echo "$f" | xargs grep -L "role-to-assume" | grep -q .',
    "find src -name '*.py' | xargs wc -l | sort -rn | head",
    "git ls-files | xargs -r grep -l TODO",
    "ls | xargs -n1 echo",
    "git ls-files | xargs -P0 grep -l TODO",  # -P0: unlimited parallelism, not NUL
    "git ls-files | xargs -I0 echo 0",  # -I0: replace-string 0
    "git ls-files | xargs -n 1 -P 4 grep -l TODO",
]
SAFE = [
    'rg -l -0 "type: governance-learning" "$VAULT/" | xargs -0 rg -l "status: candidate"',
    "git ls-files -z | xargs -0 grep -l TODO",
    "git grep -lz foo | xargs -0 -r grep -L bar",
    "find src -name '*.py' -print0 | xargs -r0 wc -l",
    "grep -rl --null x . | xargs --null grep -L y",
    "find . -print0 | xargs -n 1 -0 wc -l",  # -0 after an option value
    "find . -print0 | xargs -P 4 -r0 grep -l x",
    "find . -print0 | xargs -0P4 grep -l x",  # -0 leading a cluster
    "no pipeline here, just prose about grep",
    "inline code like `find -print0 | xargs -0` in a changelog",
    "prose that names plain `xargs` without piping to it",
]


class GuardTests(unittest.TestCase):
    def test_whitespace_split_xargs_is_flagged(self):
        for text in UNSAFE:
            with self.subTest(text=text):
                self.assertTrue(lint.unsafe_xargs(text))

    def test_nul_separated_xargs_passes(self):
        for text in SAFE:
            with self.subTest(text=text):
                self.assertFalse(lint.unsafe_xargs(text))


class CorpusTests(unittest.TestCase):
    def test_standards_use_nul_separated_xargs(self):
        for path in sorted((ROOT / "standards").rglob("*.md")):
            text = path.read_text()
            front = yaml.safe_load(FRONTMATTER.match(text).group(1))
            for v in front["verification"]:
                with self.subTest(path=path.name, cmd=v["cmd"][:60]):
                    self.assertFalse(lint.unsafe_xargs(str(v["cmd"])))
            with self.subTest(path=path.name, part="body"):
                self.assertFalse(lint.unsafe_xargs(text))

    def test_skills_use_nul_separated_xargs(self):
        for path in sorted((ROOT / "skills").rglob("SKILL.md")):
            with self.subTest(path=path.parent.name):
                self.assertFalse(lint.unsafe_xargs(path.read_text()))


def verification_cmd(standard: str, needle: str) -> str:
    """The verification cmd of standards/<standard> that contains `needle`."""
    text = (ROOT / "standards" / standard).read_text()
    front = yaml.safe_load(FRONTMATTER.match(text).group(1))
    (cmd,) = [str(v["cmd"]) for v in front["verification"] if needle in str(v["cmd"])]
    return cmd


def git_repo(files: dict[str, str]) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    if files:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return tmp


def passes(cmd: str, cwd: str) -> bool:
    """Run a verification cmd the way run-verification.py does (bash -c, project root,
    GOVERNANCE_DIR set)."""
    env = {**os.environ, "GOVERNANCE_DIR": str(ROOT)}
    proc = subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env, capture_output=True, check=False)
    return proc.returncode == 0


class VerificationCmdTests(unittest.TestCase):
    """Each fixed cmd: a noncompliant file under a spaced path fails; compliant and absent pass."""

    def check(self, cmd: str, bad: dict, good: dict) -> None:
        for name, files, expected in (
            ("bad", bad, False),
            ("good", good, True),
            ("none", {}, True),
        ):
            with self.subTest(case=name), git_repo(files) as repo:
                self.assertEqual(passes(cmd, repo), expected)

    def test_inf_envs_oidc_role(self):
        wf = ".github/workflows/deploy prod.yml"
        step = "    steps:\n      - uses: aws-actions/configure-aws-credentials@v4\n"
        self.check(
            verification_cmd("infra/inf-envs.md", "role-to-assume"),
            bad={wf: step + "        with: {aws-region: us-east-1}\n"},
            good={wf: step + "        with: {role-to-assume: arn:aws:iam::1:role/ci}\n"},
        )

    def test_inf_containers_user(self):
        self.check(
            verification_cmd("infra/inf-containers.md", "USER"),
            bad={"svc a/Dockerfile": "FROM alpine\n"},
            good={"svc a/Dockerfile": "FROM alpine\nUSER app\n"},
        )

    def test_inf_serverless_limits(self):
        lam = 'resource "aws_lambda_function" "f" {\n'
        self.check(
            verification_cmd("infra/inf-serverless.md", "aws_lambda_function"),
            bad={"infra/my lambda.tf": lam + "  timeout = 10\n}\n"},
            good={"infra/my lambda.tf": lam + "  memory_size = 256\n  timeout = 10\n}\n"},
        )


class EvolveStandardsGatherTests(unittest.TestCase):
    """/evolve-standards step 1 finds candidates named the way /harvest-learnings names them."""

    def gather_cmd(self) -> str:
        text = (ROOT / "skills" / "evolve-standards" / "SKILL.md").read_text()
        step = text.split("### 1. Gather candidates", 1)[1]
        return re.search(r"```bash\n(.*?)```", step, re.DOTALL).group(1)

    def test_finds_spaced_candidates_in_a_spaced_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp, "my vault")
            (vault / "Inbox").mkdir(parents=True)
            head = "---\ntype: governance-learning\nstatus: {}\n---\n"
            (vault / "Inbox" / "2026-11-05 governance open one.md").write_text(
                head.format("candidate")
            )
            (vault / "Inbox" / "2026-11-05 governance done one.md").write_text(
                head.format("promoted")
            )
            (vault / "Inbox" / "2026-11-05 unrelated.md").write_text("status: candidate\n")
            cmd = self.gather_cmd().replace("$VAULT", str(vault))
            proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False)
        found = sorted(Path(p).name for p in proc.stdout.splitlines() if p)
        self.assertEqual(found, ["2026-11-05 governance open one.md"], proc.stderr)


if __name__ == "__main__":
    unittest.main()
