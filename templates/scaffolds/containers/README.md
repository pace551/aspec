# Scaffold `containers/`

Canonical container assets per **INF-CONTAINERS**. `/bootstrap-repo` copies the
Dockerfile matching the project's stack to `Dockerfile`, `dockerignore` to
`.dockerignore`, and fills `{{…}}` placeholders.

| File | Destination | Purpose |
|---|---|---|
| `Dockerfile.python` | `Dockerfile` | multi-stage python build; non-root; healthcheck |
| `Dockerfile.node` | `Dockerfile` | multi-stage node build; non-root; healthcheck |
| `dockerignore` | `.dockerignore` | secrets/git/venv never enter the build context |
| `ecs-task-def.snippet.json` | merged into the tofu `aws_ecs_task_definition` | Fargate task: SSM `secrets`, awslogs, limits, healthcheck |

Notes:

- **Digest pinning (T3+, INF-CONTAINERS-03):** replace `FROM python:3.14-slim` with
  `FROM python:3.14-slim@sha256:<digest>` — get the digest with
  `docker buildx imagetools inspect python:3.14-slim`. Keep the tag alongside the digest
  so humans can still read it.
- The task definition is authored in tofu (INF-TF); the JSON snippet is the shape to
  produce, kept here because the `secrets`-vs-`environment` distinction is the part
  people get wrong (SEC-SECRETS-03).
- Local checks: `checks/inf-container-scan.sh` (hadolint + trivy config, built-in
  fallback when neither is installed).
