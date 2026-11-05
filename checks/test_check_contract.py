#!/usr/bin/env python3
"""Contract tests for every check ASPEC ships: verification cmds and checks/*.sh scanners.

Each check either has a Contract below or sits on ALLOWED with a reason. A Contract
carries a known-bad project the check must fail: a claim about how a tool behaves is only
checked by running the real tool on bad input. Checks that walk or search the tree also
get hostile cases:

- the bad file sits under a path with spaces and non-ASCII characters
- the bad file's directory is unreadable: the check must not pass (an incomplete scan is
  a failure, never a silent pass)
- unreadable, gitignored node_modules/ and .venv/ holding bad copies, a directory
  symlink loop, and nested git repos (one committed as a gitlink, one untracked): the
  check still finishes and passes

Cmds run the way run-verification.py runs them (bash -c, project root, GOVERNANCE_DIR set)
with a fixed system PATH, so optional linters on the developer's machine don't change
what is tested.
"""

from __future__ import annotations

import contextlib
import functools
import re
import subprocess
import unittest
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml
from hostile_tree import EXCLUDED_DIRS, GITIGNORE, HOSTILE_DIR, can_lock, clean_env, tree

ROOT = Path(__file__).resolve().parent.parent
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
VENV_PATH = f"{ROOT / '.venv' / 'bin'}:{SYSTEM_PATH}"
TIMEOUT = 120


@functools.cache
def catalog() -> dict[str, str]:
    """`<STANDARD-ID>#<n>` -> cmd, for every non-attestation verification cmd."""
    cmds = {}
    for path in sorted((ROOT / "standards").rglob("*.md")):
        front = yaml.safe_load(FRONTMATTER.match(path.read_text()).group(1))
        for i, v in enumerate(front.get("verification") or []):
            if not str(v["cmd"]).startswith("attest:"):
                cmds[f"{front['id']}#{i}"] = str(v["cmd"])
    return cmds


@dataclass(frozen=True)
class Contract:
    needle: str  # must appear in the cmd, so an entry can't drift onto another check
    bad: dict[str, str]  # a project the check must fail
    good: dict[str, str] | None = None  # a project the check must pass
    empty_passes: bool = True  # an empty repo passes (False: the check requires something)
    walks: bool = False  # searches the tree: also run the hostile cases
    path: str = SYSTEM_PATH
    message: str = "chore: fixture"  # commit subject of the bad fixture repo
    branch: str = "main"  # branch of the bad fixture repo
    untracked: dict[str, str] = field(default_factory=dict)  # bad case: written after commit
    hostile_names: bool = True  # walking: bad paths hold a space and non-ASCII (False: say why)
    lock: str = ""  # walking: the directory to make unreadable (default: the bad file's)
    good_git: tuple[tuple[str, ...], ...] = ()  # git commands run in the good fixture
    no_pass: str = ""  # why no fixture here can pass (else: good, or empty_passes)


H = HOSTILE_DIR
TF_LAMBDA = 'resource "aws_lambda_function" "f" {\n'
DOCKER_OK = "FROM alpine:3.20\nUSER app\n"
WF = ".github/workflows"
T3_JOBS = ("lint", "typecheck", "test", "coverage-ratchet", "gitleaks", "sast", "sca")
SHELL_TRUE = "import subprocess\n\n\ndef run(cmd):\n    return subprocess.call(cmd, shell=True)\n"
PY_CLEAN = "def add(a, b):\n    return a + b\n"
PYPROJECT = '[project]\nname = "x"\nversion = "0"\n'


def workflow(*jobs: str) -> str:
    body = "".join(
        f"  {j}:\n    runs-on: ubuntu-latest\n    steps: [{{run: 'true'}}]\n" for j in jobs
    )
    return f"on: push\njobs:\n{body}"


def fake_aws_key() -> str:
    # built at runtime so this file holds no secret-shaped literal
    return "AKIA" + "Q7" * 8


CONTRACTS: dict[str, Contract] = {
    # ---- architecture --------------------------------------------------------------
    "ARC-CONFIG#0": Contract(
        "settings.yaml",
        bad={},
        untracked={"settings.yaml": "a: 1\n"},
        good={"settings.yaml": "a: 1\n"},
    ),
    "ARC-ERRORS#0": Contract(
        "silent-swallow.py",
        bad={f"{H}/job.py": "try:\n    x = 1\nexcept Exception:\n    pass\n"},
        good={f"{H}/job.py": "try:\n    x = 1\nexcept ValueError:\n    pass\n"},
        walks=True,
    ),
    "ARC-MODULARITY#0": Contract(
        "import-cycles.py",
        bad={
            "src/pkg/__init__.py": "",
            "src/pkg/ünï/__init__.py": "",
            "src/pkg/ünï/a.py": "from pkg.ünï import b\n",
            "src/pkg/ünï/b.py": "from pkg.ünï import a\n",
        },
        good={"src/pkg/__init__.py": "", "src/pkg/a.py": "from pkg import b\n", "src/pkg/b.py": ""},
        walks=True,
        hostile_names=False,  # a Python package directory can't hold a space
        lock="src/pkg/ünï",
    ),
    # ---- data ----------------------------------------------------------------------
    "DATA-PRIVACY#0": Contract(
        "pii_inventory",
        bad={"GOVERNANCE.md": "tier: T3\n"},
        good={"GOVERNANCE.md": "pii_inventory: none\n"},
        empty_passes=False,
    ),
    "DATA-RETENTION#0": Contract(
        "retention",
        bad={"GOVERNANCE.md": "tier: T3\n"},
        good={"GOVERNANCE.md": "Retention: logs kept 30 days.\n"},
        empty_passes=False,
    ),
    # ---- infra ---------------------------------------------------------------------
    "INF-CONTAINERS#0": Contract(
        "inf-container-scan.sh",
        bad={f"{H}/Dockerfile": "FROM alpine\n", ".dockerignore": ".git\n"},
        good={f"{H}/Dockerfile": DOCKER_OK, ".dockerignore": ".git\n"},
        walks=True,
    ),
    "INF-CONTAINERS#1": Contract(
        "^USER",
        bad={f"{H}/Dockerfile": "FROM alpine:3.20\n"},
        good={f"{H}/Dockerfile": DOCKER_OK},
        walks=True,
    ),
    "INF-CONTAINERS#2": Contract(
        ".dockerignore",
        bad={f"{H}/Dockerfile": DOCKER_OK},
        good={f"{H}/Dockerfile": DOCKER_OK, ".dockerignore": ".git\n"},
    ),
    "INF-EDGE#0": Contract(
        "public-read",
        bad={f"{H}/main.tf": 'resource "aws_s3_bucket_acl" "b" {\n  acl = "public-read"\n}\n'},
        good={f"{H}/main.tf": 'resource "aws_s3_bucket_acl" "b" {\n  acl = "private"\n}\n'},
        walks=True,
    ),
    "INF-EDGE#1": Contract(
        "from_port",
        bad={f"{H}/sg.tf": "ingress {\n  from_port = 22\n  to_port = 22\n}\n"},
        good={f"{H}/sg.tf": "ingress {\n  from_port = 443\n  to_port = 443\n}\n"},
        walks=True,
    ),
    "INF-EDGE#2": Contract(
        "aws_nat_gateway",
        bad={f"{H}/net.tf": 'resource "aws_nat_gateway" "n" {}\n'},
        good={f"{H}/net.tf": 'resource "aws_vpc" "v" {}\n'},
        walks=True,
    ),
    "INF-ENVS#0": Contract(
        "AWS_SECRET_ACCESS_KEY",
        bad={
            f"{WF}/ünïcødé jobs/deploy prod.yml": "env: {K: ${{ secrets.AWS_SECRET_ACCESS_KEY }}}\n"
        },
        good={f"{WF}/ünïcødé jobs/deploy prod.yml": "on: push\n"},
        walks=True,
    ),
    "INF-ENVS#1": Contract(
        "role-to-assume",
        bad={
            f"{WF}/ünïcødé jobs/deploy prod.yml": (
                "steps:\n  - uses: aws-actions/configure-aws-credentials@v4\n"
                "    with: {aws-region: us-east-1}\n"
            )
        },
        good={
            f"{WF}/ünïcødé jobs/deploy prod.yml": (
                "steps:\n  - uses: aws-actions/configure-aws-credentials@v4\n"
                "    with: {role-to-assume: 'arn:aws:iam::1:role/ci'}\n"
            )
        },
        walks=True,
    ),
    "INF-SERVERLESS#0": Contract(
        "samconfig",
        bad={"samconfig.toml": "version = 0.1\n"},
        good={"main.tf": "\n"},
    ),
    "INF-SERVERLESS#1": Contract(
        "-e memory_size -e timeout",
        bad={f"{H}/fn.tf": TF_LAMBDA + "  timeout = 10\n}\n"},
        good={f"{H}/fn.tf": TF_LAMBDA + "  memory_size = 256\n  timeout = 10\n}\n"},
        walks=True,
    ),
    "INF-SERVERLESS#2": Contract(
        "aws_lambda_provisioned_concurrency_config",
        bad={f"{H}/fn.tf": 'resource "aws_lambda_provisioned_concurrency_config" "p" {}\n'},
        good={f"{H}/fn.tf": TF_LAMBDA + "}\n"},
        walks=True,
    ),
    "INF-TF#1": Contract(
        "tfstate",
        bad={f"{H}/terraform.tfstate": "{}\n"},
        good={f"{H}/main.tf": "\n"},
    ),
    "INF-TF#2": Contract(
        "lock",
        bad={f"{H}/main.tf": "\n"},
        good={f"{H}/main.tf": "\n", f"{H}/.terraform.lock.hcl": "\n"},
    ),
    "INF-TF#3": Contract(
        'backend \\"s3\\"',
        bad={f"{H}/main.tf": 'terraform {\n  backend "local" {}\n}\n'},
        good={f"{H}/main.tf": 'terraform {\n  backend "s3" {}\n}\n'},
        walks=True,
    ),
    "INF-TF#4": Contract(
        "default_tags",
        bad={f"{H}/main.tf": 'provider "aws" {}\n'},
        good={f"{H}/main.tf": 'provider "aws" {\n  default_tags { tags = {} }\n}\n'},
        walks=True,
    ),
    # ---- legal / ops ---------------------------------------------------------------
    "LEG-LICENSING#0": Contract(
        "license-audit",
        bad={f"{WF}/ci.yml": workflow("lint", "test")},
        good={f"{WF}/ci.yml": workflow("lint", "license-audit")},
        empty_passes=False,
    ),
    "OPS-BACKUP#0": Contract(
        "git remote",
        bad={"a.txt": "x\n"},
        good={"a.txt": "x\n"},
        good_git=(("remote", "add", "origin", "https://example.invalid/r.git"),),
        empty_passes=False,
    ),
    "OPS-OBS#0": Contract("*.log", bad={f"{H}/app run.log": "x\n"}, good={"a.txt": "x\n"}),
    "OPS-RELEASE#0": Contract(
        "CHANGELOG.md", bad={"a.txt": "x\n"}, good={"CHANGELOG.md": "# x\n"}, empty_passes=False
    ),
    # ---- process -------------------------------------------------------------------
    "DEV-BOOTSTRAP#0": Contract(
        "refs/heads/main", bad={"a.txt": "x\n"}, good={"a.txt": "x\n"}, branch="trunk"
    ),
    "DEV-BOOTSTRAP#1": Contract(
        "README.md",
        bad={"README.md": ""},
        good={"README.md": "# x\n"},
        empty_passes=False,
    ),
    "DEV-BOOTSTRAP#2": Contract(
        "CLAUDE.md", bad={"CLAUDE.md": ""}, good={"CLAUDE.md": "# x\n"}, empty_passes=False
    ),
    "DEV-BOOTSTRAP#3": Contract(
        "GOVERNANCE.md",
        bad={"GOVERNANCE.md": ""},
        good={"GOVERNANCE.md": "# x\n"},
        empty_passes=False,
    ),
    "DEV-BOOTSTRAP#4": Contract(
        ".gitignore", bad={".gitignore": ""}, good={".gitignore": ".env\n"}, empty_passes=False
    ),
    "DEV-BOOTSTRAP#6": Contract(
        ".coverage-baseline",
        bad={"a.txt": "x\n"},
        good={".coverage-baseline": "50.0\n"},
        empty_passes=False,
    ),
    "DEV-CI#0": Contract(
        "--tier T3",
        bad={f"{WF}/ci.yml": workflow(*T3_JOBS[:-1])},
        good={f"{WF}/ci.yml": workflow(*T3_JOBS)},
        empty_passes=False,
    ),
    "DEV-CI#1": Contract(
        "--tier T4",
        bad={f"{WF}/ci.yml": workflow(*T3_JOBS)},
        good={f"{WF}/ci.yml": workflow(*T3_JOBS, "license-audit")},
        empty_passes=False,
    ),
    "DEV-DEPS#0": Contract(
        "package.json",
        bad={"package.json": "{}\n"},
        good={"package.json": "{}\n", "package-lock.json": "{}\n"},
    ),
    "DEV-DEPS#2": Contract(
        "dependabot.yml",
        bad={"a.txt": "x\n"},
        good={".github/dependabot.yml": "version: 2\n"},
        empty_passes=False,
    ),
    "DEV-GIT#0": Contract(
        "git log -20", bad={"a.txt": "x\n"}, good={"a.txt": "x\n"}, message="Update stuff"
    ),
    "DEV-GIT#2": Contract(
        "symbolic-ref", bad={"a.txt": "x\n"}, good={"a.txt": "x\n"}, branch="My_Branch"
    ),
    # ---- security ------------------------------------------------------------------
    "SEC-CRYPTO#0": Contract(
        "sec-sast.sh",
        bad={"pyproject.toml": PYPROJECT, f"{H}/run.py": SHELL_TRUE},
        good={"pyproject.toml": PYPROJECT, f"{H}/run.py": PY_CLEAN},
        walks=True,
        path=VENV_PATH,
    ),
    "SEC-SECRETS#0": Contract(
        "secret-scan.sh",
        bad={f"{H}/settings.py": f'KEY_ID = "{fake_aws_key()}"\n'},
        good={f"{H}/settings.py": "KEY_ID = None\n"},
        walks=True,
    ),
    "SEC-SECRETS#1": Contract(
        "check-ignore -q .env",
        bad={".env": "A=1\n"},
        good={".gitignore": ".env\n"},
    ),
    "SEC-SECRETS#2": Contract(
        ".env.example",
        bad={".gitignore": ".env\n"},
        untracked={".env": "A=1\n"},
        good={".gitignore": ".env\n", ".env.example": "A=\n"},
    ),
    "SEC-SUPPLY#1": Contract(
        "sec-sca.sh",
        # strict tier, no pip-audit on PATH: the gate must fail, never vanish
        bad={"pyproject.toml": PYPROJECT},
        empty_passes=False,
        no_pass="passing needs pip-audit and the network (TST-FIXTURES-03 keeps tests offline)",
    ),
    # ---- stacks --------------------------------------------------------------------
    "STK-DDB#0": Contract(
        "access-patterns.md",
        bad={"a.txt": "x\n"},
        good={"docs/access-patterns.md": "| pattern |\n"},
        empty_passes=False,
    ),
    "STK-DDB#1": Contract(
        "provisionedthroughput",
        bad={f"{H}/table.tf": 'billing_mode = "PROVISIONED"\n'},
        good={f"{H}/table.tf": 'billing_mode = "PAY_PER_REQUEST"\n'},
        walks=True,
    ),
    "STK-DDB#2": Contract(
        "ScanCommand",
        bad={f"src/{H}/repo.ts": "await client.send(new ScanCommand({}))\n"},
        good={f"src/{H}/repo.ts": "await client.send(new QueryCommand({}))\n"},
        walks=True,
    ),
    "STK-NEXT#3": Contract(
        "NEXT_PUBLIC_",
        bad={f"app/{H}/page.tsx": "const k = process.env.NEXT_PUBLIC_API_SECRET\n"},
        good={f"app/{H}/page.tsx": "const k = process.env.NEXT_PUBLIC_SITE_URL\n"},
        walks=True,
    ),
    "STK-NEXT#4": Contract(
        "<img",
        bad={f"app/{H}/page.tsx": 'export default () => <img src="/a.png" />\n'},
        good={f"app/{H}/page.tsx": 'export default () => <Image src="/a.png" />\n'},
        walks=True,
    ),
    "STK-PG#0": Contract(
        "alembic.ini",
        bad={"a.txt": "x\n"},
        good={"migrations/0001_init.sql": "\n"},
        empty_passes=False,
    ),
    "STK-PG#1": Contract(
        "timestamp",
        bad={f"migrations/{H}/0001 init.sql": "create table t (at timestamp);\n"},
        good={f"migrations/{H}/0001 init.sql": "create table t (at timestamptz);\n"},
        walks=True,
    ),
    "STK-REDIS#0": Contract(
        "keys[(]",
        bad={f"src/{H}/cache.py": 'names = r.keys("user:*")\n'},
        good={f"src/{H}/cache.py": 'names = r.scan_iter("user:*")\n'},
        walks=True,
    ),
    "STK-RUST#5": Contract(
        "Cargo.lock",
        bad={"Cargo.toml": "[package]\n"},
        good={"Cargo.toml": "[package]\n", "Cargo.lock": "\n"},
        empty_passes=False,
    ),
    "STK-SQLITE#0": Contract(
        "busy_timeout",
        bad={f"{H}/db.py": 'PRAGMAS = "journal_mode=WAL; foreign_keys=ON"\n'},
        good={f"{H}/db.py": 'PRAGMAS = "journal_mode=WAL; foreign_keys=ON; busy_timeout=5000"\n'},
        empty_passes=False,
        walks=True,
    ),
    "STK-SQLITE#2": Contract(
        "migrations",
        bad={"migrations/init.sql": "\n"},
        good={"migrations/0001_init.sql": "\n"},
    ),
    "STK-SWIFT#1": Contract("Podfile", bad={"Podfile": "\n"}, good={"Package.swift": "\n"}),
    "STK-SWIFT#2": Contract(
        "ObservableObject",
        bad={f"App/{H}/Model.swift": "final class M: ObservableObject {}\n"},
        good={f"App/{H}/Model.swift": "@Observable final class M {}\n"},
        walks=True,
    ),
    "STK-SWIFT#3": Contract(
        "UserDefaults",
        bad={f"App/{H}/Store.swift": 'UserDefaults.standard.set(t, forKey: "apiToken")\n'},
        good={f"App/{H}/Store.swift": 'UserDefaults.standard.set(t, forKey: "theme")\n'},
        walks=True,
    ),
    "STK-TS#3": Contract(
        "noUncheckedIndexedAccess",
        bad={"tsconfig.json": '{"compilerOptions": {"strict": true}}\n'},
        good={
            "tsconfig.json": (
                '{"compilerOptions": {"strict": true, "noUncheckedIndexedAccess": true}}\n'
            )
        },
        empty_passes=False,
    ),
    "STK-TS#4": Contract(
        ".nvmrc",
        bad={"package.json": '{"type": "module"}\n'},
        good={"package.json": '{"type": "module"}\n', ".nvmrc": "22\n"},
        empty_passes=False,
    ),
    "STK-TS#7": Contract(
        "package-lock.json",
        bad={".gitignore": "package-lock.json\n"},
        untracked={"package-lock.json": "{}\n"},
        good={"package-lock.json": "{}\n"},
        empty_passes=False,
    ),
    "STK-VITE#2": Contract(
        "VITE_",
        bad={f"src/{H}/api.ts": "const k = import.meta.env.VITE_STRIPE_SECRET\n"},
        good={f"src/{H}/api.ts": "const k = import.meta.env.VITE_API_URL\n"},
        walks=True,
    ),
    # ---- testing -------------------------------------------------------------------
    "TST-RATCHET#1": Contract(
        ".coverage-baseline",
        bad={},
        untracked={".coverage-baseline": "50.0\n"},
        good={".coverage-baseline": "50.0\n"},
    ),
    "TST-VERIFY#2": Contract(
        "scripts/verify.sh",
        bad={"a.txt": "x\n"},
        good={"scripts/verify.sh": "#!/bin/sh\n"},
        empty_passes=False,
    ),
}

# The same script and fixtures behind several standards' cmds (one per tier).
for _key in ("SEC-CRYPTO#1", "SEC-CRYPTO#2", "SEC-INPUT#0", "SEC-INPUT#1", "SEC-INPUT#2",
             "SEC-SAST#0", "SEC-SAST#1", "SEC-SAST#2", "STK-SQLITE#1"):  # fmt: skip
    CONTRACTS[_key] = CONTRACTS["SEC-CRYPTO#0"]
# strict tiers: no manifest means no scan, and that fails
for _key in (
    "SEC-CRYPTO#1",
    "SEC-CRYPTO#2",
    "SEC-INPUT#1",
    "SEC-INPUT#2",
    "SEC-SAST#1",
    "SEC-SAST#2",
):
    CONTRACTS[_key] = replace(CONTRACTS["SEC-CRYPTO#0"], empty_passes=False)
CONTRACTS["SEC-SUPPLY#2"] = CONTRACTS["SEC-SUPPLY#1"]
CONTRACTS["TST-FIXTURES#0"] = CONTRACTS["SEC-SECRETS#0"]

TOOLCHAIN = (
    "runs the project's own toolchain ({}); its behaviour on bad input is that tool's,"
    " and the test environment doesn't install it"
)
OWN_SCRIPTS = (
    "runs the project's own scripts/{} gate, which /bootstrap-repo writes per stack;"
    " nothing of ASPEC's to test"
)
NETWORK = (
    "needs the network: {} queries a vulnerability database (TST-FIXTURES-03 keeps tests offline)"
)
COVERED = "covered by {}"

ALLOWED: dict[str, str] = {
    "DEV-BOOTSTRAP#5": COVERED.format("test_git_gate_checks.py (HookCheckTests)"),
    "DEV-CI#2": COVERED.format("test_git_gate_checks.py (HookCheckTests)"),
    "DEV-GIT#1": COVERED.format("test_git_gate_checks.py (LinearHistoryCheckTests)"),
    "INF-TF#0": (
        "inf-tf-scan.sh needs tofu/terraform, tflint or checkov to find anything, and with "
        "none installed it degrades to warnings by design; its path handling and unreadable-"
        "dir behaviour are covered by test_scan_spaced_paths.py"
    ),
    "SEC-SUPPLY#0": NETWORK.format("pip-audit (lenient tier: a missing scanner passes by design)"),
    "SEC-WEB#0": "needs a running web app; sec-web-headers.sh skips when none answers",
    "UX-A11Y#0": "needs a running web app and npx @axe-core/cli with a browser driver",
    "STK-SWIFT#0": TOOLCHAIN.format("swift / xcodebuild"),
    "STK-GO#0": TOOLCHAIN.format("gofmt"),
    "STK-GO#1": TOOLCHAIN.format("go vet"),
    "STK-GO#2": OWN_SCRIPTS.format("lint.sh"),
    "STK-GO#3": TOOLCHAIN.format("go test"),
    "STK-GO#4": TOOLCHAIN.format(
        "go test -coverprofile; the ratchet is test_coverage_ratchet.py's"
    ),
    "STK-GO#5": TOOLCHAIN.format("go mod tidy"),
    "STK-GO#6": NETWORK.format("govulncheck"),
    "STK-HTMX#0": OWN_SCRIPTS.format("test.sh"),
    "STK-HTMX#1": OWN_SCRIPTS.format("lint.sh"),
    "STK-NEXT#0": OWN_SCRIPTS.format("lint.sh"),
    "STK-NEXT#1": OWN_SCRIPTS.format("test.sh"),
    "STK-NEXT#2": TOOLCHAIN.format("playwright with browsers"),
    "STK-PY#0": TOOLCHAIN.format(".venv/bin/ruff"),
    "STK-PY#1": TOOLCHAIN.format(".venv/bin/ruff format"),
    "STK-PY#2": COVERED.format("test_python_bandit_target.py (bandit's target and config)"),
    "STK-PY#3": NETWORK.format("pip-audit"),
    "STK-PY#4": TOOLCHAIN.format(".venv/bin/pytest"),
    "STK-PY#5": TOOLCHAIN.format(
        ".venv/bin/pytest --cov; the ratchet is test_coverage_ratchet.py's"
    ),
    "STK-RUST#0": TOOLCHAIN.format("cargo fmt"),
    "STK-RUST#1": TOOLCHAIN.format("cargo clippy"),
    "STK-RUST#2": TOOLCHAIN.format("cargo test"),
    "STK-RUST#3": TOOLCHAIN.format("cargo llvm-cov; the ratchet is test_coverage_ratchet.py's"),
    "STK-RUST#4": NETWORK.format("cargo audit"),
    "STK-TS#0": TOOLCHAIN.format("prettier"),
    "STK-TS#1": TOOLCHAIN.format("eslint"),
    "STK-TS#2": TOOLCHAIN.format("tsc"),
    "STK-TS#5": TOOLCHAIN.format("vitest"),
    "STK-TS#6": TOOLCHAIN.format("vitest --coverage; the ratchet is test_coverage_ratchet.py's"),
    "STK-TS#8": NETWORK.format("npm audit"),
    "STK-VITE#0": OWN_SCRIPTS.format("lint.sh"),
    "STK-VITE#1": OWN_SCRIPTS.format("test.sh"),
    "TST-RATCHET#0": COVERED.format("test_coverage_ratchet.py (the cmd only tolerates its exit 3)"),
}

# checks/*.sh that no standard's cmd runs directly, with why they need no contract here.
SCRIPTS_ALLOWED = {
    "install.sh": "the installer, not a check: covered by test_install.py",
}


def run_cmd(cmd: str, project: Path, path: str) -> subprocess.CompletedProcess:
    env = clean_env(PATH=path, GOVERNANCE_DIR=str(ROOT), HOME=str(project.parent))
    return subprocess.run(
        ["bash", "-c", cmd],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )


class CatalogTests(unittest.TestCase):
    """Every check has a contract or a reason; no entry points at a check that's gone."""

    def test_every_cmd_has_a_contract_or_a_reason(self):
        keys = set(catalog())
        self.assertEqual(sorted(keys - CONTRACTS.keys() - ALLOWED.keys()), [], "unaccounted")
        self.assertEqual(sorted((CONTRACTS.keys() | ALLOWED.keys()) - keys), [], "stale")
        self.assertEqual(sorted(CONTRACTS.keys() & ALLOWED.keys()), [], "both")
        for key, reason in ALLOWED.items():
            self.assertGreater(len(reason), 20, key)

    def test_contracts_name_their_cmd(self):
        cmds = catalog()
        for key, c in CONTRACTS.items():
            with self.subTest(key=key):
                self.assertIn(c.needle, cmds[key])

    def test_every_scanner_script_is_exercised(self):
        cmds = catalog()
        tested = " ".join(cmds[k] for k in CONTRACTS)
        allowed = " ".join(cmds[k] for k in ALLOWED)
        for script in sorted((ROOT / "checks").glob("*.sh")):
            with self.subTest(script=script.name):
                if script.name in SCRIPTS_ALLOWED:
                    continue
                self.assertTrue(
                    f"checks/{script.name}" in tested or f"checks/{script.name}" in allowed,
                    f"{script.name}: no standard runs it; add a contract or SCRIPTS_ALLOWED",
                )

    def test_every_contract_can_pass(self):
        # a check that fails everything would satisfy its bad fixture: show it can pass
        for key, c in CONTRACTS.items():
            with self.subTest(key=key):
                self.assertTrue(c.good is not None or c.empty_passes or c.no_pass)

    def test_walking_contracts_use_hostile_paths(self):
        for key, c in CONTRACTS.items():
            if c.walks and c.hostile_names:
                with self.subTest(key=key):
                    self.assertTrue(
                        any(" " in p and not p.isascii() for p in c.bad),
                        "a walking check's bad fixture needs a path with a space and non-ASCII",
                    )


class ContractTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(can_lock(), "root can read any directory")
    def test_secret_scan_with_many_unreadable_files_is_incomplete(self):
        # hundreds of grep errors once made the "incomplete" test lose to SIGPIPE
        with tree() as t:
            t.write({f"locked/f{i:03d}.txt": "x\n" for i in range(400)})
            t.commit()
            with t.locked("locked"):
                proc = run_cmd(catalog()["SEC-SECRETS#0"], t.root, SYSTEM_PATH)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def run_case(self, key: str, c: Contract, files: dict[str, str], *, bad: bool = False,
                 lock: tuple[str, ...] = (), extra=None, loop: bool = False,
                 git: tuple[tuple[str, ...], ...] = ()):  # fmt: skip
        cmd = catalog()[key]
        with tree() as t:
            t.write(files)
            t.write(extra or {})
            if loop:
                t.symlink_loop("loops")
                t.nested_repo("vendor/lib")  # committed below: a gitlink
            t.commit(c.message if bad else "chore: fixture")
            if loop:
                t.nested_repo("scratch/clone")  # stays untracked
            if bad and c.branch != "main":
                t.git("branch", "-m", c.branch)
            if bad:
                t.write(c.untracked)
            for args in git:
                t.git(*args)
            with contextlib.ExitStack() as stack:
                for rel in lock:
                    stack.enter_context(t.locked(rel))
                return run_cmd(cmd, t.root, c.path)

    def expect(self, proc: subprocess.CompletedProcess, passes: bool, finding=False) -> None:
        """passes: exit 0. Otherwise nonzero; finding: exactly 1, a detected problem rather
        than 2 (usage error or incomplete scan), so a broken check can't pass for one."""
        detail = f"exit {proc.returncode}\n{proc.stdout}\n{proc.stderr}"
        if passes:
            self.assertEqual(proc.returncode, 0, detail)
        elif finding:
            self.assertEqual(proc.returncode, 1, detail)
        else:
            self.assertNotEqual(proc.returncode, 0, detail)

    def test_contracts(self):
        for key, c in sorted(CONTRACTS.items()):
            with self.subTest(key=key, case="bad"):
                self.expect(self.run_case(key, c, c.bad, bad=True), passes=False, finding=True)
            if c.good is not None:
                with self.subTest(key=key, case="good"):
                    self.expect(self.run_case(key, c, c.good, git=c.good_git), passes=True)
            with self.subTest(key=key, case="empty"):
                self.expect(self.run_case(key, c, {}), passes=c.empty_passes)

    def test_hostile_trees(self):
        if not can_lock():
            self.skipTest("root can read any directory")
        for key, c in sorted(CONTRACTS.items()):
            if not c.walks:
                continue
            bad_dir = c.lock or str(Path(next(p for p in c.bad if " " in p)).parent)
            with self.subTest(key=key, case="unreadable dir holding the bad file"):
                self.expect(self.run_case(key, c, c.bad, bad=True, lock=(bad_dir,)), passes=False)
            # one passing tree with every obstacle a scan must step around: unreadable,
            # gitignored node_modules/ and .venv/ holding bad copies, and a symlink loop
            good = c.good or {}
            extra = {".gitignore": GITIGNORE + (good.get(".gitignore") or "")}
            for d in EXCLUDED_DIRS:
                extra.update({f"{d}/pkg/{Path(p).name}": body for p, body in c.bad.items()})
            with self.subTest(key=key, case="unreadable excluded dirs, symlink loop, nested repos"):
                self.expect(
                    self.run_case(key, c, good, extra=extra, lock=EXCLUDED_DIRS, loop=True),
                    passes=bool(c.good) or c.empty_passes,
                )


if __name__ == "__main__":
    unittest.main()
