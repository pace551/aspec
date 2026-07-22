# Scaffold `data/postgresql/`

PostgreSQL fragment merged into a backend scaffold by `/bootstrap-repo` when the
project's `stacks` include `postgresql`. Standard: STK-PG. Local dev is dockerized;
production is always managed (RDS/Neon/Supabase — STK-PG-01).

| File | Destination in project | Purpose |
|---|---|---|
| `docker-compose.yml` | `docker-compose.yml` (or merged as the `db` service) | postgres:16-alpine with healthcheck + named volume |
| `env.fragment` | appended to `.env.example` | `DATABASE_URL` + pool-size vars (placeholder values only) |
| `pool.py.frag` | merged into the db module (e.g. `src/{pkg}/db.py`) | canonical pool config (STK-PG-03); TS projects transcribe to `pg.Pool` |
| `migrations/0001_init.sql` | `migrations/0001_init.sql` | dbmate-style skeleton; `timestamptz`, FK-index conventions baked in |

## How `/bootstrap-repo` merges this

1. If the project already has a compose file, merge the `db` service and `pgdata`
   volume instead of overwriting.
2. Append `env.fragment` to `.env.example`; put real values only in `.env`
   (gitignored, SEC-SECRETS).
3. Pick the migration tool by language — `alembic` (Python), `dbmate` (SQL-neutral),
   `drizzle-kit` (TypeScript) — and adapt the skeleton; STK-PG-02's gate looks for
   `alembic.ini` / `migrations/` / `db/migrations/` / `drizzle.config.ts`.
4. Add to the project `CLAUDE.md`: `docker compose up -d db` for local dev, the
   migrate command, and a note that the app role is least-privilege in prod
   (STK-PG-05).

## Conventions carried by this fragment

- `timestamptz` only — the STK-PG-06 gate greps migrations for the bare word
  `timestamp` and fails on it.
- Every FK gets an index in the same migration that creates it (STK-PG-04).
- The compose password `localdev` is intentionally unexciting: local-only, never
  reused anywhere real.
