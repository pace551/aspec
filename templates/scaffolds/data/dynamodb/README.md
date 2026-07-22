# Scaffold `data/dynamodb/`

DynamoDB fragment merged into a backend scaffold by `/bootstrap-repo` when the
project's `stacks` include `dynamodb`. Standard: STK-DDB. The access-pattern doc is
the deliverable that must exist before any table does (STK-DDB-01).

| File | Destination in project | Purpose |
|---|---|---|
| `access-patterns.md` | `docs/access-patterns.md` | the pattern table → key design worksheet; STK-DDB-01's gate checks it exists |
| `docker-compose.yml` | `docker-compose.yml` (or merged as a service) | DynamoDB Local for tests (STK-DDB-06) — never hand-mocked marshalling |
| `table.example.tf` | `infra/` (adapted) | on-demand single-table definition with GSI, TTL, PITR |
| `env.fragment` | appended to `.env.example` | local endpoint + dummy creds for offline SDK use |

## How `/bootstrap-repo` merges this

1. Copy `access-patterns.md` to `docs/` and STOP: filling it in is a design
   conversation with the human, not autofill. Keys and GSIs come from its rows.
2. Merge the compose service; test fixtures create tables against
   `DYNAMODB_ENDPOINT_URL` at session start (in-memory mode resets per run).
3. Adapt `table.example.tf` into the project's IaC — keep `PAY_PER_REQUEST`; the
   STK-DDB-02 gate greps for provisioned billing declarations and fails on them.
4. Append `env.fragment` to `.env.example`; prod uses task-role credentials, never
   static keys (SEC-SECRETS).
5. Add to the project `CLAUDE.md`: "reads are GetItem/Query only; Scan belongs in
   `scripts/`, not `src/` (STK-DDB-03)".

## Conventions carried by this fragment

- Single table, `PK`/`SK` string keys, entity-prefixed (`USER#<id>`).
- `expires_at` (epoch seconds) is the house TTL attribute name.
- Blobs go to S3 with a pointer attribute — items stay far below 400KB (STK-DDB-07).
