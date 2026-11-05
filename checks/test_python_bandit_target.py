#!/usr/bin/env python3
"""Unit tests for which tree bandit scans: STK-PY-04's verification cmd and sec-sast.sh.

A package scans src/ (unchanged). Without src/, a project with pyproject.toml scans the
repo with `-c pyproject.toml`, so a script collection's (STK-PY-01) [tool.bandit]
exclusions apply however the table header is written; bandit ignores a pyproject.toml
that has no [tool.bandit] table. Only a setup.py project keeps the plain `-r .`.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SEC_SAST = ROOT / "checks" / "sec-sast.sh"
_fm = re.match(
    r"\A---\n(.*?)\n---\n", (ROOT / "standards" / "stacks" / "stk-py.md").read_text(), re.DOTALL
)
STK_PY_04 = next(
    str(v["cmd"])
    for v in yaml.safe_load(_fm.group(1))["verification"]
    if v["rules"] == ["STK-PY-04"]
)

STUB = '#!/bin/sh\necho "$@" >> "$BANDIT_ARGS"\n'
PROJECT = '[project]\nname = "x"\nversion = "0.1.0"\n'


def bandit_args(layout: str, cmd: list[str]) -> str:
    with tempfile.TemporaryDirectory() as proj:
        p = Path(proj)
        if layout == "setup.py":
            (p / "setup.py").write_text("from setuptools import setup\nsetup()\n")
        else:
            pyproject = PROJECT
            if layout == "package":
                (p / "src" / "x").mkdir(parents=True)
            elif layout == "scripts":  # TOML allows a comment after a table header
                pyproject += '\n[tool.bandit]  # scan config\nexclude_dirs = ["examples"]\n'
            (p / "pyproject.toml").write_text(pyproject)
        (p / ".venv" / "bin").mkdir(parents=True)
        stub = p / ".venv" / "bin" / "bandit"
        stub.write_text(STUB)
        stub.chmod(0o755)
        record = p / "args.txt"
        subprocess.run(
            cmd,
            cwd=p,
            capture_output=True,
            check=False,
            env={**os.environ, "BANDIT_ARGS": str(record), "GOVERNANCE_DIR": str(ROOT)},
        )
        return record.read_text().strip() if record.exists() else ""


class StkPy04Tests(unittest.TestCase):
    def run_cmd(self, layout: str) -> str:
        return bandit_args(layout, ["bash", "-c", STK_PY_04])

    def test_package_scans_src(self):
        self.assertEqual(self.run_cmd("package"), "-r src -q")

    def test_script_collection_scans_repo_with_its_config(self):
        self.assertEqual(self.run_cmd("scripts"), "-c pyproject.toml -r . -q")

    def test_no_src_passes_pyproject_even_without_bandit_table(self):
        self.assertEqual(self.run_cmd("flat"), "-c pyproject.toml -r . -q")


class SecSastTests(unittest.TestCase):
    def run_script(self, layout: str) -> str:
        return bandit_args(layout, ["bash", str(SEC_SAST), "--tier", "T3"])

    def test_package_scans_src(self):
        self.assertEqual(self.run_script("package"), "-r src -q")

    def test_script_collection_scans_repo_with_its_config(self):
        self.assertEqual(self.run_script("scripts"), "-c pyproject.toml -r . -q")

    def test_no_src_passes_pyproject_even_without_bandit_table(self):
        self.assertEqual(self.run_script("flat"), "-c pyproject.toml -r . -q")

    def test_setup_py_project_scans_repo_without_config(self):
        self.assertEqual(self.run_script("setup.py"), "-r . -q")


if __name__ == "__main__":
    unittest.main()
