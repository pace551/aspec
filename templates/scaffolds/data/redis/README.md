# Scaffold `data/redis/`

Redis/Valkey fragment merged into a backend scaffold by `/bootstrap-repo` when the
project's `stacks` include `redis`. Standard: STK-REDIS. Load-bearing rule: this is a
cache/coordination layer — nothing that can't be lost lives only here (STK-REDIS-01).

| File | Destination in project | Purpose |
|---|---|---|
| `docker-compose.yml` | `docker-compose.yml` (or merged as the `cache` service) | valkey:8-alpine with explicit `maxmemory` + `allkeys-lru` (STK-REDIS-04) |
| `env.fragment` | appended to `.env.example` | `REDIS_URL` + default TTL var |

## How `/bootstrap-repo` merges this

1. Merge the `cache` service; if the project's Redis holds coordination keys that must
   not evict, change the policy per STK-REDIS-04 (split instances or `volatile-lru`) —
   deliberately, in this file, with a comment.
2. Append `env.fragment` to `.env.example`; the prod `REDIS_URL` (with AUTH token)
   comes from SSM, never a tracked file (SEC-SECRETS).
3. Generate the cache module using the canonical cache-aside shape (worked example in
   STK-REDIS): key names `{app}:{entity}:{id}` (STK-REDIS-07), `SET … EX` on every
   write (STK-REDIS-02), `scan_iter` never `.keys(pattern)` (STK-REDIS-03).
4. Start an invalidation table in the project README — one line per cached entity:
   `entity — cache-aside, <ttl>s TTL, {ttl-only | delete-on-write in <fn>}`
   (STK-REDIS-05).

## Conventions carried by this fragment

- Durable queues are SQS, not Redis lists (STK-REDIS-01, ARC-CONCURRENCY).
- Distributed locks: prefer the database's primitives; a Redis lock is `SET key token
  NX PX ms` + compare-token release, and the guarded operation tolerates lock expiry
  (STK-REDIS-08).
- Keyspace exemptions from TTL are listed in `GOVERNANCE.md`, per prefix, with reasons.
