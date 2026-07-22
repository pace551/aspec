# Canonical pool config (STK-PG-03) — merge into the project's db module.
# TypeScript equivalent: new pg.Pool({ connectionString, min, max }).
import os

from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    os.environ["DATABASE_URL"],                     # no fallback default (SEC-SECRETS)
    min_size=int(os.environ.get("PGPOOL_MIN_SIZE", "1")),
    max_size=int(os.environ.get("PGPOOL_MAX_SIZE", "10")),
)

# Usage: connections always borrowed via context manager, returned on exit:
#   with pool.connection() as conn:
#       conn.execute("SELECT ... WHERE id = %s", (some_id,))   # parameterized only
