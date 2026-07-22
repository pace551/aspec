# Scaffold `data/sqlite/`

SQLite fragment merged into a backend scaffold by `/bootstrap-repo` when the project's
`stacks` include `sqlite`. Standard: STK-SQLITE. No docker-compose — SQLite needs no
server, which is the point (STK-SQLITE-01).

| File | Destination in project | Purpose |
|---|---|---|
| `pragmas.sql` | inlined into the db connect helper (e.g. `src/{pkg}/db.py`) | canonical init block: WAL + `foreign_keys` + `busy_timeout` + `synchronous` (STK-SQLITE-02) |
| `migrate.sh` | `scripts/migrate.sh` (chmod +x) | numbered-migration runner writing `schema_migrations` (STK-SQLITE-04) |
| `migrations/0001_init.sql` | `migrations/0001_init.sql` | first migration skeleton; STRICT table example (STK-SQLITE-07) |

## How `/bootstrap-repo` merges this

1. Copy `migrations/` and `migrate.sh` as-is; replace the `example` table with the
   project's real baseline schema.
2. Generate the connect helper in the backend language, executing each pragma from
   `pragmas.sql` on every connection (Python reference implementation:
   `examples/python/`). Do not scatter pragmas per call site.
3. Add the db file and its sidecars to `.gitignore`: `*.db`, `*.db-wal`, `*.db-shm`.
4. Append to the project `CLAUDE.md`: `scripts/migrate.sh data/app.db` as the migrate
   command; note that backups use `.backup`/Litestream, never `cp` (STK-SQLITE-06).

## Conventions carried by this fragment

- Migrations are forward-only, `NNNN_description.sql`, numbers never reused.
- Migration files contain no `BEGIN`/`COMMIT` — the runner owns the transaction.
- Verify: `bash ~/Dev/claude-code/governance/checks/sec-sast.sh` (no string-built SQL)
  and the STK-SQLITE pragma grep both pass on a fresh merge because this fragment
  ships the pragma block and a numbered migration.
