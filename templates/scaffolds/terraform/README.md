# Scaffold `terraform/`

OpenTofu skeleton per **INF-TF**: one root module per environment under `envs/`,
composing shared modules under `modules/`. `/bootstrap-repo` copies this tree into the
project (usually as `infra/`), fills `{{PROJECT}}`, and appends `gitignore` to the
project `.gitignore`.

```
infra/
├── envs/
│   ├── dev/            # root module for dev — its own state, its own backend
│   │   ├── backend.tf.example   # copy to backend.tf once the state bucket exists
│   │   ├── main.tf              # composes ../../modules/*
│   │   ├── variables.tf
│   │   └── versions.tf          # pinned core+providers, default_tags
│   └── prod/           # same shape; Env tag and state key differ
└── modules/
    └── s3-private-bucket/       # example shared module (private, versioned, encrypted)
```

## First-apply order (C6: spend requires consent)

1. Get explicit approval for the resources and their monthly cost estimate.
2. Create the **budget alarm first** (`OPS-FINOPS`) — before any other resource.
3. Create the state bucket once per AWS account (outside tofu — it holds the state):
   `aws s3api create-bucket --bucket {{PROJECT}}-tofu-state ...` then enable versioning.
4. `cp backend.tf.example backend.tf`, fill in the bucket, `tofu init`.
5. `tofu plan` → read it → `tofu apply` (T3: laptop OK after plan review; T4: CI only).

Native S3 locking (`use_lockfile = true`) is the default — no DynamoDB table to pay for
or manage. The commented `dynamodb_table` line is the fallback for CLIs older than 1.10.

Checks: `checks/inf-tf-scan.sh` runs fmt/validate/tflint/checkov over any `*.tf` dirs;
CI runs the same via `templates/ci/_fragments/iac-scan.yml`.
