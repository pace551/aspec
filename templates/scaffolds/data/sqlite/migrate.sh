#!/usr/bin/env bash
# Apply numbered migrations/NNNN_*.sql not yet recorded in schema_migrations
# (STK-SQLITE-04). Forward-only; each file runs inside one transaction together
# with its version row. Migration files must NOT contain BEGIN/COMMIT themselves.
# Usage: scripts/migrate.sh path/to/app.db
set -euo pipefail

DB="${1:?usage: migrate.sh path/to/app.db}"

sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
) STRICT;"

for f in migrations/[0-9]*_*.sql; do
  [ -e "$f" ] || { echo "no migrations found"; exit 0; }
  v="$(basename "$f" .sql)"
  applied="$(sqlite3 "$DB" "SELECT 1 FROM schema_migrations WHERE version = '$v';")"
  [ -n "$applied" ] && continue
  echo "applying $v"
  sqlite3 "$DB" <<SQL
PRAGMA foreign_keys = ON;
BEGIN;
$(cat "$f")
INSERT INTO schema_migrations (version) VALUES ('$v');
COMMIT;
SQL
done
echo "schema up to date"
